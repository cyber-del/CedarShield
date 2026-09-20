import boto3, time
cfn = boto3.client("cloudformation", region_name="ap-southeast-2")
try:
    cfn.delete_stack(StackName="cedarshield-amplify-stack")
    print("Deleting stack...")
except Exception as e:
    print(e)
