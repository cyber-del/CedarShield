import boto3

cfn = boto3.client("cloudformation", region_name="ap-southeast-2")
events = cfn.describe_stack_events(StackName="cedarshield-stack")["StackEvents"]
for e in events:
    if e.get("LogicalResourceId") in ("FrontendServerFunction", "ApiRouterFunction"):
        print(f"{e.get('LogicalResourceId')}: {e.get('ResourceStatus')} -> {e.get('ResourceStatusReason')}")
