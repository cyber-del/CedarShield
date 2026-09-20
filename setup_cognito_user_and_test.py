import json
import boto3
import urllib.request
import urllib.error
import time

REGION = "ap-southeast-2"
USER_POOL_ID = "ap-southeast-2_QGbPPwecZ"
CLIENT_ID = "5v5di986mlbftuo81vvspu1qcd"
API_URL = "https://mwrzzbhzu8.execute-api.ap-southeast-2.amazonaws.com/prod"
USERNAME = "security-reviewer@example.com"
PASSWORD = "ReviewerPass#2026!Sec"

cognito = boto3.client("cognito-idp", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table("cedarshield-audit-log")

print("=" * 70)
print("1. PROVISIONING COGNITO USER")
print("=" * 70)

# Create user if not already exists
try:
    user_res = cognito.admin_create_user(
        UserPoolId=USER_POOL_ID,
        Username=USERNAME,
        UserAttributes=[
            {"Name": "email", "Value": USERNAME},
            {"Name": "email_verified", "Value": "true"}
        ],
        MessageAction="SUPPRESS"
    )
    print(f"Created user: {USERNAME}")
    print(f"User Sub: {user_res['User']['Username']}")
except cognito.exceptions.UsernameExistsException:
    print(f"User {USERNAME} already exists.")

# Set permanent password
cognito.admin_set_user_password(
    UserPoolId=USER_POOL_ID,
    Username=USERNAME,
    Password=PASSWORD,
    Permanent=True
)
print("Set permanent password successfully.")

print("\n" + "=" * 70)
print("2. REAL COGNITO AUTHENTICATION FLOW (ADMIN_INITIATE_AUTH)")
print("=" * 70)

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

print(f"Auth Flow Successful!")
print(f"Token Type: {token_type}")
print(f"Expires In: {expires_in} seconds")
print(f"ID Token (first 60 chars): {id_token[:60]}...")
print(f"Access Token (first 60 chars): {access_token[:60]}...")

print("\n" + "=" * 70)
print("3. TEST UNAUTHENTICATED CALL TO /approve (EXPECT 401 UNAUTHORIZED)")
print("=" * 70)

test_run_id = f"cognito-verify-run-{int(time.time())}"
req_payload = json.dumps({"run_id": test_run_id}).encode("utf-8")

# Attempt without Authorization header
unauth_req = urllib.request.Request(
    f"{API_URL}/approve",
    data=req_payload,
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(unauth_req) as response:
        print(f"UNEXPECTED SUCCESS: {response.getcode()}")
        print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP Status: {e.code} {e.reason}")
    print(f"Response Body: {e.read().decode()}")
    print("Unauthenticated access successfully blocked by Cognito JWT authorizer!")

print("\n" + "=" * 70)
print("4. TEST AUTHENTICATED CALL TO /approve WITH VALID COGNITO JWT")
print("=" * 70)

# First seed the test run in DynamoDB so /approve can find it
table.put_item(
    Item={
        "run_id": test_run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "AWAITING_APPROVAL",
        "principal": "CedarShield-FinanceAgent-Role",
        "action": "process_refund",
        "arguments": {"amount": 2000, "refund_id": "ref-cognito-001"},
        "patch": {
            "proposed_policy": 'permit (\n    principal == CedarShield::Role::"CedarShield-FinanceAgent-Role",\n    action == CedarShield::Action::"process_refund",\n    resource\n) when {\n    context.amount <= 2500\n};'
        },
        "approver_identity": "PENDING"
    }
)
print(f"Seeded run record '{test_run_id}' in DynamoDB Table 'cedarshield-audit-log'.")

# Send /approve with Authorization: Bearer <id_token>
auth_req = urllib.request.Request(
    f"{API_URL}/approve",
    data=req_payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {id_token}"
    }
)

try:
    with urllib.request.urlopen(auth_req) as response:
        print(f"HTTP Status: {response.getcode()} OK")
        auth_resp_body = response.read().decode()
        print("Response Body:")
        print(json.dumps(json.loads(auth_resp_body), indent=2))
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode()}")

print("\n" + "=" * 70)
print("5. VERIFY DYNAMODB AUDIT RECORD APPROVER IDENTITY")
print("=" * 70)

updated_item = table.get_item(Key={"run_id": test_run_id}).get("Item", {})
print(f"Run ID: {updated_item.get('run_id')}")
print(f"Status: {updated_item.get('status')}")
print(f"Approver Identity in Audit Log: {updated_item.get('approver_identity')}")
print(f"Approved At: {updated_item.get('approved_at')}")
print(f"Policy Applied: {updated_item.get('policy_applied')}")

print("\n" + "=" * 70)
print("6. CONFIRM OPEN ENDPOINTS (/trigger-denial and /audit-log)")
print("=" * 70)

audit_req = urllib.request.Request(f"{API_URL}/audit-log")
with urllib.request.urlopen(audit_req) as resp:
    print(f"GET /audit-log Status (Open Demo Route): {resp.getcode()} OK")
    body = json.loads(resp.read().decode())
    print(f"Audit log returned {len(body.get('items', []))} records without requiring JWT.")

print("\nCOGNITO AUTHENTICATION VERIFICATION COMPLETE!")
