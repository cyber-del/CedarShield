import json
import requests
import botocore.session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

s = botocore.session.get_session()
creds = s.get_credentials().get_frozen_credentials()

base_url = "https://cedarshieldgateway-pgs4beuirv.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com"

tests = [
    ("/process-refund", {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "process_refund", "arguments": {"amount": 250}}}),
    ("/delete-resource", {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "delete_resource", "arguments": {"resource_id": "db-1"}}}),
    ("/mcp", {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "delete_resource", "arguments": {"resource_id": "db-1"}}}),
    ("/mcp", {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "delete-resource", "arguments": {"resource_id": "db-1"}}})
]

for path, payload in tests:
    url = f"{base_url}{path}"
    body = json.dumps(payload)
    req = AWSRequest(method="POST", url=url, data=body, headers={"Content-Type": "application/json"})
    SigV4Auth(creds, "bedrock-agentcore", "ap-southeast-2").add_auth(req)
    r = requests.post(url, headers=dict(req.headers), data=body)
    print(f"\nTarget: {path} | Method: {payload['params']['name']}")
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
