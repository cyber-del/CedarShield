import boto3

lambda_client = boto3.client("lambda", region_name="ap-southeast-2")
try:
    resp = lambda_client.list_functions()
    print(f"Successfully listed {len(resp.get('Functions', []))} Lambda functions.")
    for f in resp.get("Functions", []):
        if "CedarShield" in f["FunctionName"] or "cedarshield" in f["FunctionName"]:
            print(" -", f["FunctionName"], f["Role"])
except Exception as e:
    print("Lambda client error:", e)
