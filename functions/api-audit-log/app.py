import json
import os
import boto3

DYNAMODB_TABLE = os.environ.get("AUDIT_TABLE_NAME", "cedarshield-audit-log")
REGION = os.environ.get("AWS_REGION_NAME", "ap-southeast-2")

dynamodb = boto3.resource("dynamodb", region_name=REGION)

def lambda_handler(event, context):
    """
    GET /audit-log
    Retrieves all Cedar denial diagnosis, remediation patches, and approval records.
    """
    print("AuditLogFunction received event:", json.dumps(event, default=str))
    
    table = dynamodb.Table(DYNAMODB_TABLE)
    try:
        resp = table.scan()
        items = resp.get("Items", [])
        
        # Sort items by timestamp descending
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Parse nested json strings if stored as strings
        formatted_items = []
        for item in items:
            formatted = dict(item)
            for k in ["arguments", "diagnosis", "patch", "adversarial_tests", "verification"]:
                if k in formatted and isinstance(formatted[k], str):
                    try:
                        formatted[k] = json.loads(formatted[k])
                    except Exception:
                        pass
            formatted_items.append(formatted)
            
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({
                "count": len(formatted_items),
                "items": formatted_items,
                "runs": formatted_items
            }, default=str)
        }
    except Exception as e:
        print(f"Error reading audit log: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}, default=str)
        }
