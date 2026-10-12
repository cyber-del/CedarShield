import boto3

iam = boto3.client("iam")
try:
    for p in iam.list_role_policies(RoleName="AccountFullAccessRole")["PolicyNames"]:
        print("Inline policy:", p)
        print(iam.get_role_policy(RoleName="AccountFullAccessRole", PolicyName=p))
except Exception as e:
    print("Error listing role policies:", e)
