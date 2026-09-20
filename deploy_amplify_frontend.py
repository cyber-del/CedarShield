import os
import io
import time
import zipfile
import requests
import boto3

REGION = "ap-southeast-2"
APP_NAME = "CedarShield-WebUI"
BRANCH_NAME = "main"
DIST_DIR = "frontend/dist"

amplify = boto3.client("amplify", region_name=REGION)

print("=" * 80)
print(f"DEPLOYING CEDARSHIELD FRONTEND TO AWS AMPLIFY HOSTING ({REGION})")
print("=" * 80)

# 1. Check or Create Amplify App
apps = amplify.list_apps()["apps"]
target_app = next((a for a in apps if a["name"] == APP_NAME), None)

if not target_app:
    print(f"Creating new AWS Amplify App: {APP_NAME}...")
    create_res = amplify.create_app(
        name=APP_NAME,
        description="CedarShield Autonomous Policy Remediation Web Platform",
        platform="WEB",
        customRules=[
            {
                "source": "</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|woff2|ttf|map|json)$)([^.]+$)/>",
                "target": "/index.html",
                "status": "200"
            }
        ]
    )
    target_app = create_res["app"]
    print(f"Created Amplify App ID: {target_app['appId']}")
else:
    print(f"Found existing Amplify App: {target_app['name']} (ID: {target_app['appId']})")

app_id = target_app["appId"]
default_domain = target_app.get("defaultDomain", f"{app_id}.amplifyapp.com")

# 2. Check or Create Branch
branches = amplify.list_branches(appId=app_id)["branches"]
target_branch = next((b for b in branches if b["branchName"] == BRANCH_NAME), None)

if not target_branch:
    print(f"Creating branch '{BRANCH_NAME}' in Amplify App...")
    create_branch_res = amplify.create_branch(
        appId=app_id,
        branchName=BRANCH_NAME,
        stage="PRODUCTION",
        enableAutoBuild=False
    )
    target_branch = create_branch_res["branch"]
    print(f"Created branch: {BRANCH_NAME}")
else:
    print(f"Found existing branch: {BRANCH_NAME}")

# 3. Create Zip Archive of frontend/dist
print(f"\nPackaging '{DIST_DIR}' into deployment zip archive...")
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(DIST_DIR):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, DIST_DIR)
            z.write(full_path, rel_path)
            print(f"  Added to bundle: {rel_path}")

zip_bytes = zip_buffer.getvalue()
print(f"Bundle size: {len(zip_bytes) / 1024:.1f} KB")

# 4. Create Deployment on Amplify
print("\nCreating Amplify deployment session...")
deployment = amplify.create_deployment(
    appId=app_id,
    branchName=BRANCH_NAME
)
job_id = deployment["jobId"]
upload_url = deployment["zipUploadUrl"]
print(f"Created deployment Job ID: {job_id}")

# 5. Upload zip to S3 via pre-signed URL
print("Uploading bundle to AWS Amplify...")
upload_res = requests.put(
    upload_url,
    data=zip_bytes,
    headers={"Content-Type": "application/zip"}
)
upload_res.raise_for_status()
print("Bundle upload successful (HTTP 200)!")

# 6. Start Deployment
print("Starting deployment on Amplify...")
amplify.start_deployment(
    appId=app_id,
    branchName=BRANCH_NAME,
    jobId=job_id
)

# 7. Monitor Deployment Status
print("Waiting for deployment to complete...")
live_url = f"https://{BRANCH_NAME}.{default_domain}"

for attempt in range(30):
    time.sleep(3)
    job = amplify.get_job(appId=app_id, branchName=BRANCH_NAME, jobId=job_id)["job"]
    status = job["summary"]["status"]
    print(f"  Attempt {attempt + 1}: Deployment status = {status}")
    if status == "SUCCEED":
        print("\n" + "=" * 80)
        print("AMPLIFY DEPLOYMENT SUCCEEDED!")
        print(f"Live Public URL: {live_url}")
        print("=" * 80)
        break
    elif status == "FAILED":
        print(f"\nDeployment failed: {job.get('summary', {}).get('reason')}")
        exit(1)
