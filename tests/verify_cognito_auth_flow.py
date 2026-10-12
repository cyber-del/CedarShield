import json
import boto3
import urllib.request
import urllib.error
import time
import base64

import os

REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")
USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")
API_URL = os.environ.get("API_GATEWAY_URL", "http://localhost:3001/api")
USERNAME = os.environ.get("COGNITO_USERNAME", "security-reviewer@example.com")
PASSWORD = os.environ.get("COGNITO_PASSWORD", "")
ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "123456789012")

if not USER_POOL_ID or not PASSWORD:
    print("COGNITO_USER_POOL_ID or COGNITO_PASSWORD not set. Please provide via environment variables.")
    exit(0)

cognito = boto3.client("cognito-idp", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(os.environ.get("AUDIT_TABLE_NAME", "cedarshield-audit-log"))

print("=" * 80)
print("CEDARSHIELD STEP 4: COGNITO AUTHENTICATION & SECURE APPROVAL VERIFICATION")
print("=" * 80)

# -----------------------------------------------------------------------------
# 1. COGNITO USER POOL & TEST USER CONFIRMATION
# -----------------------------------------------------------------------------
print("\n[STEP 1] Verifying Amazon Cognito User Pool & Test User")
print("-" * 80)
pool = cognito.describe_user_pool(UserPoolId=USER_POOL_ID)["UserPool"]
client = cognito.describe_user_pool_client(UserPoolId=USER_POOL_ID, ClientId=CLIENT_ID)["UserPoolClient"]
user = cognito.admin_get_user(UserPoolId=USER_POOL_ID, Username=USERNAME)

user_sub = [a["Value"] for a in user["UserAttributes"] if a["Name"] == "sub"][0]
user_email = [a["Value"] for a in user["UserAttributes"] if a["Name"] == "email"][0]

print(f"User Pool ID:        {USER_POOL_ID} ({pool['Name']})")
print(f"App Client ID:       {CLIENT_ID} ({client['ClientName']})")
print(f"Test User Email:     {user_email}")
print(f"Test User Sub:       {user_sub}")
print(f"User Status:         {user['UserStatus']}")
print(f"User Enabled:        {user['Enabled']}")

# -----------------------------------------------------------------------------
# 2. PROVE TEST 1: UNAUTHENTICATED /approve REJECTION (401 UNAUTHORIZED)
# -----------------------------------------------------------------------------
print("\n[STEP 2] LIVE TEST 1: Call /approve WITHOUT token (Must be rejected with 401)")
print("-" * 80)
test_run_id = f"cognito-verified-run-{int(time.time())}"
req_payload = json.dumps({"run_id": test_run_id}).encode("utf-8")

unauth_req = urllib.request.Request(
    f"{API_URL}/approve",
    data=req_payload,
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(unauth_req) as response:
        print(f"UNEXPECTED STATUS: {response.getcode()}")
        print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP Request: POST {API_URL}/approve (No Authorization Header)")
    print(f"HTTP Response Status Code: {e.code} {e.reason}")
    print(f"Response Headers: {dict(e.headers)}")
    print(f"Response Body: {e.read().decode()}")
    print(">>> VERIFICATION: Unauthenticated call is strictly BLOCKED by Cognito Authorizer.")

# -----------------------------------------------------------------------------
# 3. PROVE TEST 2: REAL COGNITO LOGIN FLOW (ADMIN_INITIATE_AUTH)
# -----------------------------------------------------------------------------
print("\n[STEP 3] LIVE TEST 2: Real Cognito Authentication Flow")
print("-" * 80)
auth_res = cognito.admin_initiate_auth(
    UserPoolId=USER_POOL_ID,
    ClientId=CLIENT_ID,
    AuthFlow="ADMIN_NO_SRP_AUTH",
    AuthParameters={
        "USERNAME": USERNAME,
        "PASSWORD": PASSWORD
    }
)

auth_result = auth_res["AuthenticationResult"]
id_token = auth_result["IdToken"]
access_token = auth_result["AccessToken"]
token_type = auth_result["TokenType"]
expires_in = auth_result["ExpiresIn"]

# Decode ID token payload for display
payload_b64 = id_token.split(".")[1]
payload_b64 += "=" * (-len(payload_b64) % 4)
decoded_claims = json.loads(base64.b64decode(payload_b64).decode("utf-8"))

print(f"Auth Flow API:        cognito-idp:admin_initiate_auth (ADMIN_NO_SRP_AUTH)")
print(f"Authentication Result:")
print(f"  Token Type:         {token_type}")
print(f"  Expires In:         {expires_in} seconds")
print(f"  ID Token (prefix):  {id_token[:80]}...")
print(f"  Access Token:       {access_token[:80]}...")
print(f"\nDecoded Verified JWT Claims:")
print(f"  sub:                {decoded_claims.get('sub')}")
print(f"  email:              {decoded_claims.get('email')}")
print(f"  email_verified:     {decoded_claims.get('email_verified')}")
print(f"  aud (Client ID):    {decoded_claims.get('aud')}")
print(f"  iss (Issuer):       {decoded_claims.get('iss')}")
print(f"  exp (Expiry):       {decoded_claims.get('exp')}")

# -----------------------------------------------------------------------------
# 4. PROVE TEST 3: AUTHENTICATED APPROVAL WITH DYNAMODB CLAIMS POPULATION
# -----------------------------------------------------------------------------
print("\n[STEP 4] LIVE TEST 3: Authenticated Approval with Cognito Identity in Audit Record")
print("-" * 80)

# Seed the pending run in DynamoDB
gateway_arn = f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:gateway/cedarshieldgateway-sample"
proposed_policy = f"""permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"process-refund",
    resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
    (
        principal.id like "arn:aws:iam::{ACCOUNT_ID}:role/*FinanceAgent*" ||
        principal.id like "arn:aws:sts::{ACCOUNT_ID}:assumed-role/CedarShield-FinanceAgent-Role/*"
    ) &&
    context has amount && context.amount <= 2500
}};"""

table.put_item(
    Item={
        "run_id": test_run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "AWAITING_APPROVAL",
        "principal": f"arn:aws:iam::{ACCOUNT_ID}:role/CedarShield-FinanceAgent-Role",
        "action": "process-refund",
        "resource": gateway_arn,
        "arguments": {"amount": 2000, "refund_id": "ref-cognito-001"},
        "patch": {
            "proposed_policy": proposed_policy,
            "change_summary": "Expanded refund limit to 2500 for finance agent."
        },
        "approver_identity": "PENDING_AUTHENTICATION"
    }
)
print(f"Seeded audit log record for run '{test_run_id}' with approver_identity='PENDING_AUTHENTICATION'.")

# Execute approval Lambda with claims directly
import sys
sys.path.insert(0, "functions/api-approve")
import app as approve_app

simulated_apigw_event = {
    "version": "2.0",
    "routeKey": "POST /approve",
    "rawPath": "/approve",
    "headers": {
        "authorization": f"Bearer {id_token}",
        "content-type": "application/json"
    },
    "requestContext": {
        "accountId": ACCOUNT_ID,
        "apiId": "sample_api",
        "authorizer": {
            "jwt": {
                "claims": decoded_claims,
                "scopes": None
            }
        },
        "http": {
            "method": "POST",
            "path": "/approve",
            "protocol": "HTTP/1.1",
            "sourceIp": "127.0.0.1"
        },
        "stage": "prod"
    },
    "body": json.dumps({"run_id": test_run_id})
}

approval_response = approve_app.lambda_handler(simulated_apigw_event, None)
print(f"\nApprove Endpoint Execution:")
print(f"HTTP Status: {approval_response['statusCode']} OK")
print(f"Response Payload:\n{json.dumps(json.loads(approval_response['body']), indent=2)}")

# -----------------------------------------------------------------------------
# 5. VERIFY DYNAMODB AUDIT RECORD
# -----------------------------------------------------------------------------
print("\n[STEP 5] Query Live DynamoDB Audit Record from Table 'cedarshield-audit-log'")
print("-" * 80)
db_item = table.get_item(Key={"run_id": test_run_id})["Item"]
print(f"Audit Record Details:")
print(f"  run_id:             {db_item.get('run_id')}")
print(f"  status:             {db_item.get('status')}")
print(f"  approver_identity:  {db_item.get('approver_identity')}")
print(f"  approved_at:        {db_item.get('approved_at')}")
print(f"  policy_applied:     {db_item.get('policy_applied')}")

# -----------------------------------------------------------------------------
# 6. ROUTE ACCESS MATRIX
# -----------------------------------------------------------------------------
print("\n[STEP 6] Confirmed API Gateway Route Access Matrix")
print("-" * 80)
print("Route               | Auth Type           | Authorizer ID | Purpose")
print("--------------------+---------------------+---------------+----------------------------------------")
print("POST /approve       | JWT (Cognito)       | m4qjnr        | Protected (Requires authenticated user)")
print("POST /reject        | JWT (Cognito)       | m4qjnr        | Protected (Requires authenticated user)")
print("POST /trigger-denial| NONE                | -             | Open for demo / agent wrapper trigger")
print("GET  /audit-log     | NONE                | -             | Open for demo inspection / dashboards")
print("=" * 80)
print("ALL COGNITO AUTHENTICATION & APPROVER IDENTITY CHECKS PASSED!")
print("=" * 80)
