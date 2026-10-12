"""
CedarShield Demo Agent: Live AgentCore Gateway Client
Invokes tools through Bedrock AgentCore Gateway with IAM SigV4 signing
and captures real AgentCore Policy Cedar DENIAL responses.
"""
import sys
import json
import requests
import botocore.session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

GATEWAY_BASE_URL = "https://cedarshieldgateway-pgs4beuirv.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com"
REGION = "ap-southeast-2"
SERVICE = "bedrock-agentcore"

def call_gateway_target(target_name: str, payload: dict, caller_label: str = "Support Agent (Non-Admin)"):
    session = botocore.session.get_session()
    credentials = session.get_credentials().get_frozen_credentials()

    url = f"{GATEWAY_BASE_URL}/{target_name}"
    body = json.dumps(payload)

    headers = {
        "Content-Type": "application/json",
        "Host": "cedarshieldgateway-pgs4beuirv.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com"
    }

    aws_request = AWSRequest(method="POST", url=url, data=body, headers=headers)
    SigV4Auth(credentials, SERVICE, REGION).add_auth(aws_request)

    print("\n" + "=" * 70)
    print(f" Caller Identity: {caller_label}")
    print(f" Target Endpoint: POST {url}")
    print(f" Request Payload: {json.dumps(payload, indent=2)}")
    print("=" * 70)

    response = requests.post(url, headers=dict(aws_request.headers), data=body, timeout=10)
    print(f" HTTP Response Status: {response.status_code}")
    print(f" Response Headers: {json.dumps(dict(response.headers), indent=2)}")
    try:
        resp_json = response.json()
        print(f" Response Payload (JSON):\n{json.dumps(resp_json, indent=2)}")
        return resp_json
    except Exception:
        print(f" Response Payload (Raw):\n{response.text}")
        return {"raw": response.text, "status_code": response.status_code}

if __name__ == "__main__":
    print("\n--- 1. Testing Live AgentCore Gateway: read-record ---")
    call_gateway_target("read-record", {"record_id": "cust_1001"}, caller_label="Support / Finance Agent")

    print("\n--- 2. Testing Live AgentCore Gateway: process-refund ---")
    call_gateway_target("process-refund", {"amount": 250, "reason": "Damaged goods return"}, caller_label="Finance Agent")

    print("\n--- 3. Testing Live AgentCore Gateway DENIAL: delete-resource (Enforced by Cedar Policy Engine) ---")
    call_gateway_target("delete-resource", {"resource_id": "prod-cluster-01"}, caller_label="Support Agent (Non-Admin)")
