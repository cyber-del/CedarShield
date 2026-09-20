import boto3
import time
import requests
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

c = boto3.client('bedrock-agentcore-control', region_name='ap-southeast-2')
engine_id = 'CedarShieldPolicyEngine-2ivsrp1osh'
gateway_arn = 'arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv'
gateway_url = 'https://cedarshieldgateway-pgs4beuirv.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com/mcp'

stmt = f"""permit (
    principal,
    action == AgentCore::Action::"read-record",
    resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
    context has record_id
}};"""

print("Deploying Candidate 1: when { context has record_id }...", flush=True)
c.update_policy(
    policyEngineId=engine_id,
    policyId='ReadRecordPolicy-x9jjxu0t2g',
    definition={'cedar': {'statement': stmt}}
)

for _ in range(15):
    time.sleep(1)
    p = c.get_policy(policyEngineId=engine_id, policyId='ReadRecordPolicy-x9jjxu0t2g')
    print("Status:", p['status'], flush=True)
    if p['status'] == 'ACTIVE':
        print("ACTIVE!", flush=True)
        break

sts = boto3.client('sts', region_name='ap-southeast-2')
assumed = sts.assume_role(
    RoleArn='arn:aws:iam::097935663941:role/CedarShield-SupportAgent-Role',
    RoleSessionName='test-sess',
    DurationSeconds=900
)
creds = boto3.Session(
    aws_access_key_id=assumed['Credentials']['AccessKeyId'],
    aws_secret_access_key=assumed['Credentials']['SecretAccessKey'],
    aws_session_token=assumed['Credentials']['SessionToken']
).get_credentials().get_frozen_credentials()

payload = {
    "jsonrpc": "2.0",
    "id": "test-candidate-1",
    "method": "tools/call",
    "params": {
        "name": "read-record___read_record",
        "arguments": {"record_id": "rec_customer_001"}
    }
}
body = json.dumps(payload)
req = AWSRequest(method="POST", url=gateway_url, data=body, headers={"Content-Type": "application/json"})
SigV4Auth(creds, "bedrock-agentcore", "ap-southeast-2").add_auth(req)

res = requests.post(gateway_url, headers=dict(req.headers), data=body, timeout=15)
print("\n=== RESPONSE ===", flush=True)
print("HTTP Status:", res.status_code, flush=True)
print("Payload:\n", json.dumps(res.json(), indent=2), flush=True)
