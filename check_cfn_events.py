import boto3

cfn = boto3.client("cloudformation", region_name="ap-southeast-2")
events = cfn.describe_stack_events(StackName="cedarshield-stack")["StackEvents"]
for e in events[:25]:
    status = e.get("ResourceStatus", "")
    if "FAIL" in status or "ROLLBACK" in status:
        print(f"{e.get('LogicalResourceId')}: {status} -> {e.get('ResourceStatusReason')}")
