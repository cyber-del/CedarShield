import boto3
import json

lam = boto3.client("lambda", region_name="ap-southeast-2")
fn_name = "cedarshield-stack-AuditLogFunction-FVmBlG1QtF6g"

try:
    resp = lam.invoke(
        FunctionName=fn_name,
        Payload=json.dumps({"rawPath": "/audit-log", "requestContext": {"http": {"method": "GET"}}}).encode("utf-8")
    )
    payload = json.loads(resp["Payload"].read().decode("utf-8"))
    print("Invoke SUCCESS:", payload)
except Exception as e:
    print("Invoke error:", e)
