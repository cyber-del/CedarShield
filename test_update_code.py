import boto3

lambda_client = boto3.client("lambda", region_name="ap-southeast-2")
try:
    resp = lambda_client.update_function_code(
        FunctionName="cedarshield-stack-AuditLogFunction-FVmBlG1QtF6g",
        S3Bucket="cedarshield-artifacts-097935663941-ap-southeast-2",
        S3Key="lambda-code/api-audit-log.zip"
    )
    print("update_function_code SUCCESS! CodeSha256:", resp.get("CodeSha256"))
except Exception as e:
    print("update_function_code error:", e)
