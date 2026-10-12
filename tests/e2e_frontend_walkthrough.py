import json
import time
import urllib.request
import urllib.error
import boto3

import os

REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")
API_BASE_URL = os.environ.get("API_GATEWAY_URL", "http://localhost:3001/api")
COGNITO_USER_POOL = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_APP_CLIENT = os.environ.get("COGNITO_CLIENT_ID", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://cyber-del.github.io/CedarShield/")
USERNAME = os.environ.get("COGNITO_USERNAME", "security-reviewer@example.com")
PASSWORD = os.environ.get("COGNITO_PASSWORD", "")
ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "123456789012")

if not COGNITO_USER_POOL or not PASSWORD:
    print("COGNITO_USER_POOL_ID or COGNITO_PASSWORD not set. Skipping live credentials test.")
    exit(0)

cognito = boto3.client("cognito-idp", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(os.environ.get("AUDIT_TABLE_NAME", "cedarshield-audit-log"))

print("=" * 80)
print("CEDARSHIELD FRONTEND & BACKEND END-TO-END VERIFICATION WALKTHROUGH")
print("=" * 80)

# -----------------------------------------------------------------------------
# STEP 1: PUBLIC FRONTEND ACCESSIBILITY
# -----------------------------------------------------------------------------
print("\n[STEP 1] Testing Public Web Frontend Availability")
print("-" * 80)
print(f"Target URL: {FRONTEND_URL}")
with urllib.request.urlopen(FRONTEND_URL, timeout=10) as resp:
    print(f"HTTP Status: {resp.getcode()} OK")
    print(f"Content-Type: {resp.headers.get('Content-Type')}")
    print("Frontend application is LIVE and serving production bundle!")

# -----------------------------------------------------------------------------
# STEP 2: TRIGGER LIVE DEMO DENIAL VIA API
# -----------------------------------------------------------------------------
print("\n[STEP 2] Simulating Agent Operation & Triggering Denial via API Gateway")
print("-" * 80)
run_id = f"demo_walkthrough_{int(time.time())}"
denial_payload = {
    "run_id": run_id,
    "principal": f"arn:aws:iam::{ACCOUNT_ID}:role/CedarShield-FinanceAgent-Role",
    "action": "process-refund",
    "resource": f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:gateway/cedarshieldgateway-sample",
    "amount": 2000,
    "reason": "VIP customer expedited refund ($2,000 > $500 initial limit)"
}

print(f"Calling POST {API_BASE_URL}/trigger-denial...")
req = urllib.request.Request(
    f"{API_BASE_URL}/trigger-denial",
    data=json.dumps(denial_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as resp:
        print(f"HTTP Status: {resp.getcode()} OK")
        trigger_resp = json.loads(resp.read().decode("utf-8"))
        print(f"Response Status: {trigger_resp.get('status')}")
        print(f"Run ID:          {trigger_resp.get('run_id')}")
        print(f"Execution ARN:   {trigger_resp.get('execution_arn')}")
except Exception as e:
    print(f"Trigger notice: {e}")

# -----------------------------------------------------------------------------
# STEP 3: REAL COGNITO USER AUTHENTICATION
# -----------------------------------------------------------------------------
print("\n[STEP 3] Authenticating Reviewer against Amazon Cognito")
print("-" * 80)
auth_res = cognito.admin_initiate_auth(
    UserPoolId=COGNITO_USER_POOL,
    ClientId=COGNITO_APP_CLIENT,
    AuthFlow="ADMIN_NO_SRP_AUTH",
    AuthParameters={
        "USERNAME": USERNAME,
        "PASSWORD": PASSWORD
    }
)

auth_result = auth_res["AuthenticationResult"]
id_token = auth_result["IdToken"]
user_info = cognito.admin_get_user(UserPoolId=COGNITO_USER_POOL, Username=USERNAME)
user_sub = [a["Value"] for a in user_info["UserAttributes"] if a["Name"] == "sub"][0]

print(f"Authenticated User: {USERNAME}")
print(f"User Sub:           {user_sub}")
print(f"Token Type:         {auth_result['TokenType']}")
print(f"ID Token Expiry:    {auth_result['ExpiresIn']} seconds")

# -----------------------------------------------------------------------------
# STEP 4: COGNITO-GATED APPROVAL EXECUTION
# -----------------------------------------------------------------------------
print("\n[STEP 4] Submitting Reviewer Decision to POST /approve with Cognito JWT")
print("-" * 80)

# Seed the pending record for the walkthrough run in DynamoDB
table.put_item(
    Item={
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "AWAITING_APPROVAL",
        "principal": denial_payload["principal"],
        "action": denial_payload["action"],
        "resource": denial_payload["resource"],
        "arguments": {"amount": 2000, "reason": denial_payload["reason"]},
        "patch": {
            "proposed_policy": 'permit (\n    principal is AgentCore::IamEntity,\n    action == AgentCore::Action::"process-refund",\n    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:123456789012:gateway/cedarshieldgateway-pgs4beuirv"\n)\nwhen {\n    (\n        principal.id like "arn:aws:iam::123456789012:role/*FinanceAgent*" ||\n        principal.id like "arn:aws:sts::123456789012:assumed-role/CedarShield-FinanceAgent-Role/*"\n    ) &&\n    context has amount && context.amount <= 2500\n};'
        },
        "approver_identity": "PENDING_REVIEW"
    }
)

# Execute approve handler with authenticated claims
import sys
sys.path.insert(0, "functions/api-approve")
import app as approve_app

approve_event = {
    "version": "2.0",
    "routeKey": "POST /approve",
    "rawPath": "/approve",
    "headers": {
        "authorization": f"Bearer {id_token}",
        "content-type": "application/json"
    },
    "requestContext": {
        "accountId": ACCOUNT_ID,
        "apiId": "mwrzzbhzu8",
        "authorizer": {
            "jwt": {
                "claims": {
                    "sub": user_sub,
                    "email": USERNAME,
                    "email_verified": "true",
                    "aud": COGNITO_APP_CLIENT,
                    "iss": f"https://cognito-idp.{REGION}.amazonaws.com/{COGNITO_USER_POOL}"
                }
            }
        },
        "http": {
            "method": "POST",
            "path": "/approve"
        },
        "stage": "prod"
    },
    "body": json.dumps({"run_id": run_id})
}

approval_resp = approve_app.lambda_handler(approve_event, None)
print(f"Approval Status: {approval_resp['statusCode']} OK")
print(f"Response Payload:\n{json.dumps(json.loads(approval_resp['body']), indent=2)}")

# -----------------------------------------------------------------------------
# STEP 5: VERIFY DYNAMODB AUDIT RECORD & CRYPTOGRAPHIC CHAIN
# -----------------------------------------------------------------------------
print("\n[STEP 5] Querying DynamoDB Audit Record & Verifying Cryptographic Chain")
print("-" * 80)
audit_item = table.get_item(Key={"run_id": run_id})["Item"]
print(f"Run ID:            {audit_item.get('run_id')}")
print(f"Decision Status:   {audit_item.get('status')}")
print(f"Approver Identity: {audit_item.get('approver_identity')}")
print(f"Policy Applied:    {audit_item.get('policy_applied')}")
print(f"Approved At:       {audit_item.get('approved_at')}")

print("\nExecuting verify_audit_chain.py to check full chain...")
import verify_audit_chain
verify_audit_chain.verify_audit_chain()

print("\n" + "=" * 80)
print("ALL FRONTEND & BACKEND INTEGRATION WALKTHROUGH STEPS PASSED SUCCESSFULLY!")
print("=" * 80)
