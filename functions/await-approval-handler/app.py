import json
import os
import boto3
from datetime import datetime

DYNAMODB_TABLE = os.environ.get("AUDIT_TABLE_NAME", "cedarshield-audit-log")
REGION = os.environ.get("AWS_REGION_NAME", "ap-southeast-2")

dynamodb = boto3.resource("dynamodb", region_name=REGION)

def lambda_handler(event, context):
    """
    Handles Step Functions Task Token registration for human-in-the-loop approval.
    """
    print("AwaitApprovalHandler received event:", json.dumps(event))
    
    token = event.get("token")
    execution_id = event.get("execution_id")
    pipeline_data = event.get("pipeline_data", {})
    run_id = pipeline_data.get("run_id")
    
    table = dynamodb.Table(DYNAMODB_TABLE)
    try:
        table.update_item(
            Key={"run_id": run_id},
            UpdateExpression="SET task_token = :t, execution_id = :ex, #st = :st, approval_requested_at = :ts",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":t": token,
                ":ex": execution_id,
                ":st": "AWAITING_APPROVAL",
                ":ts": datetime.utcnow().isoformat() + "Z"
            }
        )
        print(f"Task token successfully stored for run_id {run_id}")
    except Exception as e:
        print(f"Failed to store task token: {e}")
        
    return {
        "status": "AWAITING_APPROVAL",
        "run_id": run_id,
        "message": "Task token registered. Waiting for human approval via API Gateway."
    }
