import boto3
import time

cfn = boto3.client("cloudformation", region_name="ap-southeast-2")
st = cfn.describe_stacks(StackName="cedarshield-stack")["Stacks"][0]
print("Stack status:", st["StackStatus"])
print("Reason:", st.get("StackStatusReason"))

res = cfn.describe_stack_resources(StackName="cedarshield-stack")["StackResources"]
update_failed = [r["LogicalResourceId"] for r in res if r.get("ResourceStatus") == "UPDATE_FAILED"]
print("Resources currently in UPDATE_FAILED state:", update_failed)

if update_failed:
    cfn.continue_update_rollback(StackName="cedarshield-stack", ResourcesToSkip=update_failed)
    print("Triggered continue_update_rollback with:", update_failed)
    while True:
        time.sleep(3)
        curr = cfn.describe_stacks(StackName="cedarshield-stack")["Stacks"][0]["StackStatus"]
        print("  Status:", curr)
        if "IN_PROGRESS" not in curr:
            break
