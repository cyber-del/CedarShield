import json
import requests
import botocore.session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

s = botocore.session.get_session()
creds = s.get_credentials().get_frozen_credentials()
gateway_url = "https://cedarshieldgateway-pgs4beuirv.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com/mcp"

def call_mcp(method, params=None):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    body = json.dumps(payload)
    headers = {"Content-Type": "application/json"}
    req = AWSRequest(method="POST", url=gateway_url, data=body, headers=headers)
    SigV4Auth(creds, "bedrock-agentcore", "ap-southeast-2").add_auth(req)
    r = requests.post(gateway_url, headers=dict(req.headers), data=body)
    print(f"[{method}] -> Status: {r.status_code} | Body: {r.text}")
    return r.json()

# 1. Initialize
call_mcp("initialize", {
    "protocolVersion": "2025-03-26",
    "capabilities": {},
    "clientInfo": {"name": "DemoAgent", "version": "1.0.0"}
})

# 2. List tools
call_mcp("tools/list")

# 3. Call tool with different name combinations
call_mcp("tools/call", {"name": "delete_resource", "arguments": {"resource_id": "db-1"}})
call_mcp("tools/call", {"name": "delete-resource___delete_resource", "arguments": {"resource_id": "db-1"}})
call_mcp("tools/call", {"name": "delete-resource/delete_resource", "arguments": {"resource_id": "db-1"}})
call_mcp("tools/call", {"name": "delete-resource:delete_resource", "arguments": {"resource_id": "db-1"}})
