import boto3
import time

cfn = boto3.client("cloudformation", region_name="ap-southeast-2")
st = cfn.describe_stacks(StackName="cedarshield-stack")["Stacks"][0]
print("Stack status:", st["StackStatus"])
print("Reason:", st.get("StackStatusReason"))

# Get failed resources from stack resources
res = cfn.describe_stack_resources(StackName="cedarshield-stack")["StackResources"]
failed_res = [r["LogicalResourceId"] for r in res if "FAIL" in r.get("ResourceStatus", "")]
print("Failed resources:", failed_res)

# Try continue rollback skipping failed resources if needed
try:
    cfn.continue_update_rollback(StackName="cedarshield-stack", ResourcesToSkip=failed_res if failed_res else None)
    print("Continue rollback triggered.")
except Exception as e:
    print("Error triggering continue rollback:", e)

while True:
    time.sleep(3)
    curr = cfn.describe_stacks(StackName="cedarshield-stack")["Stacks"][0]["StackStatus"]
    print("  Status:", curr)
    if "IN_PROGRESS" not in curr:
        break
