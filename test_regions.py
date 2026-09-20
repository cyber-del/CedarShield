import boto3

for reg in ["ap-southeast-2", "us-east-1", "us-west-2", "ap-south-1"]:
    try:
        lam = boto3.client("lambda", region_name=reg)
        fns = lam.list_functions()
        print(f"Region {reg}: SUCCESS ({len(fns.get('Functions', []))} functions)")
    except Exception as e:
        print(f"Region {reg}: FAILED -> {e}")
