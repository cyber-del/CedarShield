"""
Test Gateway Invocation & Authorization
"""
import json
import requests
import botocore.session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

s = botocore.session.get_session()
creds = s.get_credentials().get_frozen_credentials()
gateway_url = "https://cedarshieldgateway-pgs4beuirv.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com"

def invoke(path, method, payload, extra_headers=None):
    url = f"{gateway_url}{path}"
    body = json.dumps(payload) if payload else ""
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)

    req = AWSRequest(method=method, url=url, data=body, headers=headers)
    SigV4Auth(creds, "bedrock-agentcore", "ap-southeast-2").add_auth(req)

    res = requests.request(method, url, headers=dict(req.headers), data=body)
    print(f"\n[INVOKE] {method} {path}")
    print(f"Status: {res.status_code}")
    print(f"Headers: {dict(res.headers)}")
    print(f"Body: {res.text}")
    return res

if __name__ == "__main__":
    # 1. MCP initialize handshake
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "CedarShieldDemoAgent", "version": "1.0.0"}
        }
    }
    invoke("/mcp", "POST", init_payload)

    # 2. Call tool through /mcp
    call_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "delete-resource",
            "arguments": {"resource_id": "db-production-01"}
        }
    }
    invoke("/mcp", "POST", call_payload)
