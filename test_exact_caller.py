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

session = boto3.Session(region_name='ap-southeast-2')
creds = session.get_credentials().get_frozen_credentials()
caller_arn = boto3.client('sts', region_name='ap-southeast-2').get_caller_identity()['Arn']
print(f"Caller ARN: {caller_arn}", flush=True)

stmt = f"""permit (
    principal == AgentCore::IamEntity::"{caller_arn}",
    action == AgentCore::Action::"read-record",
    resource == AgentCore::Gateway::"{gateway_arn}"
);"""

print("Deploying exact Caller ARN policy...", flush=True)
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
    if p['status'] == 'UPDATE_FAILED':
        print("FAILED:", p.get('statusReasons'), flush=True)
        break

payload = {
    "jsonrpc": "2.0",
    "id": "exact-test-1",
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
print("\n=== LIVE GATEWAY RESPONSE ===", flush=True)
print("HTTP Status:", res.status_code, flush=True)
print("Payload:\n", json.dumps(res.json(), indent=2), flush=True)
