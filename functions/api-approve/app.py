import json
import os
import boto3
from datetime import datetime

DYNAMODB_TABLE = os.environ.get("AUDIT_TABLE_NAME", "cedarshield-audit-log")
REGION = os.environ.get("AWS_REGION_NAME", "ap-southeast-2")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
sfn = boto3.client("stepfunctions", region_name=REGION)

def get_agentcore_client():
    try:
        return boto3.client("bedrock-agentcore-control", region_name=REGION)
    except Exception as e:
        print(f"Warning initializing bedrock-agentcore-control client: {e}")
        return None

def lambda_handler(event, context):
    """
    POST /approve
    Approves the proposed Cedar patch, unblocks Step Functions via Task Token,
    and applies the patch to the live Bedrock AgentCore Policy Engine.
    """
    print("ApproveFunction received event:", json.dumps(event, default=str))
    
    body = {}
    if "body" in event and event["body"]:
        try:
            body = json.loads(event["body"])
        except Exception:
            body = {}
            
    run_id = body.get("run_id")
    if not run_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Missing required field 'run_id'"})
        }
        
    table = dynamodb.Table(DYNAMODB_TABLE)
    item_resp = table.get_item(Key={"run_id": run_id})
    item = item_resp.get("Item")
    if not item:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": f"Run ID '{run_id}' not found"})
        }
        
    task_token = item.get("task_token")
    patch_data = {}
    if "patch" in item:
        patch_data = json.loads(item["patch"]) if isinstance(item["patch"], str) else item["patch"]
        
    proposed_policy = patch_data.get("proposed_policy")
    
    # 1. Unblock Step Functions if task token exists
    if task_token:
        try:
            sfn.send_task_success(
                taskToken=task_token,
                output=json.dumps({
                    "status": "APPROVED",
                    "run_id": run_id,
                    "approved_at": datetime.utcnow().isoformat() + "Z"
                })
            )
            print(f"Sent task success to Step Functions for token {task_token}")
        except Exception as e:
            print(f"Warning sending task success: {e}")

    # 2. Deploy patch to AgentCore Policy Engine
    applied = False
    policy_id = "ProcessRefundPolicy-kryp2370fb"
    engine_id = "CedarShieldPolicyEngine-2ivsrp1osh"
    if proposed_policy:
        try:
            agentcore = get_agentcore_client()
            if agentcore:
                agentcore.update_policy(
                    policyEngineId=engine_id,
                    policyId=policy_id,
                    definition={"cedar": {"statement": proposed_policy}}
                )
                applied = True
                print(f"Live Policy Engine updated with proposed policy")
        except Exception as pe:
            print(f"Policy Engine update error: {pe}")

    # 3. Extract Cognito Authenticated User Identity from JWT claims
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    jwt_data = authorizer.get("jwt", {})
    claims = jwt_data.get("claims", {})
    approver_email = claims.get("email") or claims.get("cognito:username") or claims.get("username")
    approver_sub = claims.get("sub", "")
    
    if approver_email and approver_sub:
        approver_identity = f"{approver_email} (sub: {approver_sub})"
    elif approver_email:
        approver_identity = approver_email
    elif approver_sub:
        approver_identity = f"sub:{approver_sub}"
    else:
        approver_identity = body.get("approver_identity", "security-reviewer@example.com")

    # 4. Update DynamoDB Audit Log Record
    table.update_item(
        Key={"run_id": run_id},
        UpdateExpression="SET #st = :st, approved_at = :ts, policy_applied = :ap, approver_identity = :appr",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":st": "APPROVED",
            ":ts": datetime.utcnow().isoformat() + "Z",
            ":ap": applied,
            ":appr": approver_identity
        }
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization"
        },
        "body": json.dumps({
            "status": "SUCCESS",
            "decision": "APPROVED",
            "run_id": run_id,
            "approver_identity": approver_identity,
            "policy_applied": applied,
            "message": f"Remediation patch for run {run_id} was successfully approved by {approver_identity} and deployed to AgentCore Policy Engine."
        })
    }
