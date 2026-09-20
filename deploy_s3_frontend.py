import os
import mimetypes
import boto3
import json
import urllib.request

REGION = "ap-southeast-2"
BUCKET = "cedarshield-web-097935663941-ap-southeast-2"
DIST_DIR = "frontend/dist"

s3 = boto3.client("s3", region_name=REGION)

print("=" * 80)
print(f"DEPLOYING CEDARSHIELD FRONTEND TO AWS S3 STATIC WEBSITE ({REGION})")
print("=" * 80)

# 1. Bucket Website Configuration
print("Configuring S3 Bucket Website...")
s3.put_bucket_website(
    Bucket=BUCKET,
    WebsiteConfiguration={
        "IndexDocument": {"Suffix": "index.html"},
        "ErrorDocument": {"Key": "index.html"}
    }
)

# 2. Disable Public Access Block & Apply Public Read Policy
try:
    s3.put_public_access_block(
        Bucket=BUCKET,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False
        }
    )
except Exception as e:
    print(f"  Note on block public access: {e}")

policy_doc = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{BUCKET}/*"
        }
    ]
}

try:
    s3.put_bucket_policy(Bucket=BUCKET, Policy=json.dumps(policy_doc))
    print("  Bucket policy applied for public read access.")
except Exception as pe:
    print(f"  Bucket policy notice: {pe}")

# 3. Upload built assets from frontend/dist
print(f"\nUploading production assets from '{DIST_DIR}' to s3://{BUCKET}...")

content_type_map = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".png": "image/png"
}

for root, dirs, files in os.walk(DIST_DIR):
    for f in files:
        full_path = os.path.join(root, f)
        rel_path = os.path.relpath(full_path, DIST_DIR).replace("\\", "/")
        ext = os.path.splitext(f)[1].lower()
        content_type = content_type_map.get(ext, "application/octet-stream")
        
        with open(full_path, "rb") as fp:
            s3.put_object(
                Bucket=BUCKET,
                Key=rel_path,
                Body=fp.read(),
                ContentType=content_type
            )
        print(f"  Uploaded: {rel_path} ({content_type})")

website_url = f"http://{BUCKET}.s3-website-{REGION}.amazonaws.com"
print("\n" + "=" * 80)
print(f"CEDARSHIELD FRONTEND LIVE PUBLIC URL: {website_url}")
print("=" * 80)

# Verify HTTP access
try:
    with urllib.request.urlopen(website_url, timeout=10) as resp:
        print(f"Verification HTTP Status: {resp.getcode()} OK")
        html_preview = resp.read().decode("utf-8")[:120]
        print(f"HTML Content Preview: {html_preview}...")
except Exception as e:
    print(f"Website ping: {e}")
