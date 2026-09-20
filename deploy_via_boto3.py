import os
import io
import zipfile
import boto3
import time
import json

REGION = "ap-southeast-2"
BUCKET = "cedarshield-artifacts-097935663941-ap-southeast-2"
STACK_NAME = "cedarshield-stack"

s3 = boto3.client("s3", region_name=REGION)
cfn = boto3.client("cloudformation", region_name=REGION)

def package_function(func_dir):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(func_dir):
            for f in files:
                if f.endswith(".pyc") or "__pycache__" in root:
                    continue
                path = os.path.join(root, f)
                rel_path = os.path.relpath(path, func_dir)
                z.write(path, rel_path)
    buf.seek(0)
    return buf.read()

print("1. Packaging and uploading Lambda functions to S3...", flush=True)
function_dirs = [d for d in os.listdir("functions") if os.path.isdir(os.path.join("functions", d))]
uploaded_keys = {}

for fdir in function_dirs:
    full_path = os.path.join("functions", fdir)
    data = package_function(full_path)
    s3_key = f"lambda-code/{fdir}.zip"
    s3.put_object(Bucket=BUCKET, Key=s3_key, Body=data)
    uploaded_keys[fdir] = s3_key
    print(f"  Uploaded {fdir} -> s3://{BUCKET}/{s3_key}", flush=True)

print("\n2. Processing CloudFormation template...", flush=True)
with open("template.yaml", "r") as f:
    template_text = f.read()

# Replace CodeUri with S3 location in template
# For SAM templates, we can replace CodeUri: functions/<name>/ with s3://bucket/lambda-code/<name>.zip
for fdir, s3_key in uploaded_keys.items():
    template_text = template_text.replace(f"CodeUri: functions/{fdir}/", f"CodeUri: s3://{BUCKET}/{s3_key}")
    template_text = template_text.replace(f"CodeUri: functions/{fdir}", f"CodeUri: s3://{BUCKET}/{s3_key}")

print("\n3. Waiting for stack to be in a ready state...", flush=True)
while True:
    st = cfn.describe_stacks(StackName=STACK_NAME)["Stacks"][0]["StackStatus"]
    print(f"  Current stack status: {st}", flush=True)
    if "IN_PROGRESS" not in st:
        break
    time.sleep(3)

print("\nCreating ChangeSet on CloudFormation...", flush=True)
change_set_name = f"cs-{int(time.time())}"

cfn.create_change_set(
    StackName=STACK_NAME,
    TemplateBody=template_text,
    Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
    ChangeSetName=change_set_name,
    ChangeSetType="UPDATE"
)

print(f"Waiting for ChangeSet {change_set_name} to be created...", flush=True)
for _ in range(30):
    time.sleep(2)
    cs = cfn.describe_change_set(StackName=STACK_NAME, ChangeSetName=change_set_name)
    status = cs["Status"]
    print(f"  ChangeSet status: {status}", flush=True)
    if status == "CREATE_COMPLETE":
        break
    if status == "FAILED":
        print(f"  ChangeSet FAILED: {cs.get('StatusReason')}", flush=True)
        # Check if no changes
        if "didn't contain changes" in cs.get("StatusReason", ""):
            print("No changes in stack.")
            exit(0)
        exit(1)

print("\n4. Executing ChangeSet...", flush=True)
cfn.execute_change_set(StackName=STACK_NAME, ChangeSetName=change_set_name)

print("Waiting for Stack Update to complete...", flush=True)
while True:
    time.sleep(5)
    st = cfn.describe_stacks(StackName=STACK_NAME)["Stacks"][0]
    status = st["StackStatus"]
    print(f"  Stack status: {status}", flush=True)
    if status in ("UPDATE_COMPLETE", "CREATE_COMPLETE"):
        print("\nStack updated successfully!", flush=True)
        for out in st.get("Outputs", []):
            print(f"  {out['OutputKey']}: {out['OutputValue']}", flush=True)
        break
    if "FAILED" in status or "ROLLBACK" in status:
        print(f"\nStack update failed with status {status}")
        # Print recent stack events
        events = cfn.describe_stack_events(StackName=STACK_NAME)["StackEvents"]
        for ev in events[:10]:
            print(f"  {ev.get('ResourceStatus')} {ev.get('LogicalResourceId')}: {ev.get('ResourceStatusReason')}")
        exit(1)
