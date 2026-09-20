import boto3
cfn = boto3.client("cloudformation", region_name="ap-southeast-2")
events = cfn.describe_stack_events(StackName="cedarshield-amplify-stack")["StackEvents"]
for ev in events[:10]:
    print(ev.get("ResourceStatus"), ev.get("LogicalResourceId"), ":", ev.get("ResourceStatusReason"))
