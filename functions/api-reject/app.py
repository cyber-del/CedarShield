import json
import os
import boto3
from datetime import datetime

DYNAMODB_TABLE = os.environ.get("AUDIT_TABLE_NAME", "cedarshield-audit-log")
REGION = os.environ.get("AWS_REGION_NAME", "ap-southeast-2")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
sfn = boto3.client("stepfunctions", region_name=REGION)

def lambda_handler(event, context):
    """
    POST /reject
    Rejects the proposed Cedar patch, cancels the Step Functions execution via Task Token,
    and updates the audit log.
    """
    print("RejectFunction received event:", json.dumps(event, default=str))
    
    body = {}
    if "body" in event and event["body"]:
        try:
            body = json.loads(event["body"])
        except Exception:
            body = {}
            
    run_id = body.get("run_id")
    reason = body.get("reason", "Human security reviewer rejected the policy expansion.")
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
    if task_token:
        try:
            sfn.send_task_failure(
                taskToken=task_token,
                error="HumanReviewerRejected",
                cause=reason
            )
            print(f"Sent task failure to Step Functions for token {task_token}")
        except Exception as e:
            print(f"Warning sending task failure: {e}")

    # Extract Cognito Authenticated User Identity from JWT claims
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

    table.update_item(
        Key={"run_id": run_id},
        UpdateExpression="SET #st = :st, rejected_at = :ts, rejection_reason = :r, approver_identity = :appr",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":st": "REJECTED",
            ":ts": datetime.utcnow().isoformat() + "Z",
            ":r": reason,
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
            "decision": "REJECTED",
            "run_id": run_id,
            "approver_identity": approver_identity,
            "message": f"Remediation patch for run {run_id} was rejected by {approver_identity}."
        })
    }
