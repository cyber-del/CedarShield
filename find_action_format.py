import json
import time
import requests
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

c = boto3.client('bedrock-agentcore-control', region_name='ap-southeast-2')
engine_id = 'CedarShieldPolicyEngine-2ivsrp1osh'
policy_id = 'ReadRecordPolicy-x9jjxu0t2g'
gateway_arn = 'arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv'
gateway_url = 'https://cedarshieldgateway-pgs4beuirv.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com/mcp'

session = boto3.Session(region_name='ap-southeast-2')
creds = session.get_credentials().get_frozen_credentials()

def test_action(action_str):
    stmt = f"""permit (
        principal,
        action == AgentCore::Action::"{action_str}",
        resource == AgentCore::Gateway::"{gateway_arn}"
    );"""
    print(f"\n--- Testing Cedar Action: {action_str} ---")
    c.update_policy(
        policyEngineId=engine_id,
        policyId=policy_id,
        definition={'cedar': {'statement': stmt}}
    )
    for _ in range(15):
        p = c.get_policy(policyEngineId=engine_id, policyId=policy_id)
        if p['status'] == 'ACTIVE':
            break
        time.sleep(1)
    
    # Now call MCP
    payload = {
        "jsonrpc": "2.0",
        "id": "test",
        "method": "tools/call",
        "params": {
            "name": "read-record___read_record",
            "arguments": {"record_id": "rec_001"}
        }
    }
    body = json.dumps(payload)
    headers = {"Content-Type": "application/json"}
    req = AWSRequest(method="POST", url=gateway_url, data=body, headers=headers)
    SigV4Auth(creds, "bedrock-agentcore", "ap-southeast-2").add_auth(req)
    r = requests.post(gateway_url, headers=dict(req.headers), data=body, timeout=10)
    print("Result:", r.text)
    return r.json()

actions_to_try = [
    "read-record___read_record",
    "read-record",
    "read_record",
    "V7O1JS4FKT", # target ID
    "read-record:read_record",
    "read-record/read_record"
]

for act in actions_to_try:
    try:
        res = test_action(act)
        if "result" in res or "error" in res and res["error"]["code"] != -32002:
            print(f">>> FOUND WORKING ACTION: {act} <<<")
            break
    except Exception as e:
        print("Error:", e)
