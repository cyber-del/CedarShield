import boto3

iam = boto3.client("iam")
try:
    role = iam.get_role(RoleName="AccountFullAccessRole")
    print("Role:", role)
    policies = iam.list_attached_role_policies(RoleName="AccountFullAccessRole")
    print("Attached policies:", policies)
except Exception as e:
    print("IAM error:", e)
