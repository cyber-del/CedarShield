import json
import requests
import botocore.session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

s = botocore.session.get_session()
creds = s.get_credentials().get_frozen_credentials()

base_url = "https://cedarshieldgateway-pgs4beuirv.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com"

payload = json.dumps({
    "jsonrpc": "2.0",
    "id": "probe-1",
    "method": "tools/list",
    "params": {}
})

paths = ["/", "/mcp", "/v1/mcp", "/tools/list", "/mcp/v1"]

for p in paths:
    url = f"{base_url}{p}"
    req = AWSRequest(method="POST", url=url, data=payload, headers={"Content-Type": "application/json"})
    SigV4Auth(creds, "bedrock-agentcore", "ap-southeast-2").add_auth(req)
    try:
        r = requests.post(url, headers=dict(req.headers), data=payload, timeout=5)
        print(f"Path: {p} -> Status: {r.status_code} | Body: {r.text[:200]}")
    except Exception as e:
        print(f"Path: {p} -> Error: {e}")
