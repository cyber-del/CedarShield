import json
import os
import boto3
from datetime import datetime

DYNAMODB_TABLE = os.environ.get("AUDIT_TABLE_NAME", "cedarshield-audit-log")
REGION = os.environ.get("AWS_REGION_NAME", "ap-southeast-2")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
events_client = boto3.client("events", region_name=REGION)
sfn_client = boto3.client("stepfunctions", region_name=REGION)

def lambda_handler(event, context):
    """
    POST /trigger-denial
    Simulates or causes a policy denial, publishes the denial event to EventBridge,
    and initiates the remediation Step Functions pipeline.
    """
    print("TriggerDenialFunction received event:", json.dumps(event, default=str))
    
    body = {}
    if "body" in event and event["body"]:
        try:
            body = json.loads(event["body"])
        except Exception:
            body = {}
            
    run_id = body.get("run_id", f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    principal = body.get("principal", "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role")
    action = body.get("action", "process-refund")
    resource = body.get("resource", "arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv")
    amount = body.get("amount", 2000)
    reason = body.get("reason", "High-value VIP refund attempt")
    force_fail = body.get("force_fail", False)
    
    arguments = {
        "amount": amount,
        "reason": reason,
        "force_fail": force_fail
    }
    
    current_policy = f"""// Policy: Process Refund
permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"process-refund",
    resource == AgentCore::Gateway::"{resource}"
)
when {{
    (
        principal.id like "arn:aws:iam::097935663941:role/*FinanceAgent*" ||
        principal.id like "arn:aws:sts::097935663941:assumed-role/CedarShield-FinanceAgent-Role/*"
    ) &&
    context has amount && context.amount <= 500
}};"""

    denial_payload = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "principal": principal,
        "action": action,
        "resource": resource,
        "arguments": arguments,
        "denial_reason": "Tool Execution Denied: Tool call not allowed due to policy enforcement [No policy applies to the request (denied by default).]",
        "current_policy": current_policy,
        "retry_count": 0
    }
    
    # 1. Store in DynamoDB
    table = dynamodb.Table(DYNAMODB_TABLE)
    try:
        table.put_item(
            Item={
                "run_id": run_id,
                "timestamp": denial_payload["timestamp"],
                "principal": principal,
                "action": action,
                "resource": resource,
                "arguments": json.dumps(arguments),
                "denial_reason": denial_payload["denial_reason"],
                "current_policy": current_policy,
                "status": "DENIED"
            }
        )
    except Exception as dbe:
        print(f"DynamoDB error: {dbe}")

    # 2. Publish to EventBridge
    eb_resp = None
    try:
        eb_resp = events_client.put_events(
            Entries=[
                {
                    "Source": "cedarshield.gateway",
                    "DetailType": "CedarShield.PolicyDenied",
                    "Detail": json.dumps(denial_payload),
                    "EventBusName": "default"
                }
            ]
        )
        print("Published EventBridge event:", eb_resp)
    except Exception as ebe:
        print(f"EventBridge publish error: {ebe}")

    # 3. Start Step Functions Execution
    execution_arn = None
    if STATE_MACHINE_ARN:
        try:
            sfn_resp = sfn_client.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=f"{run_id}",
                input=json.dumps(denial_payload)
            )
            execution_arn = sfn_resp.get("executionArn")
            print(f"Started Step Functions execution: {execution_arn}")
        except Exception as sfne:
            print(f"Step Functions start error: {sfne}")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps({
            "status": "DENIAL_CAPTURED",
            "run_id": run_id,
            "execution_arn": execution_arn,
            "eventbridge_published": True,
            "denial": denial_payload
        })
    }
