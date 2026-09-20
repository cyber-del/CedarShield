import boto3

iam = boto3.client("iam")
try:
    print("Listing roles:")
    for r in iam.list_roles()["Roles"]:
        if "CedarShield" in r["RoleName"]:
            print(f"  {r['RoleName']} -> {r['Arn']}")
except Exception as e:
    print("IAM list_roles error:", e)
