"""
CedarShield Demo Agent: Live Bedrock AgentCore Policy & Gateway Verification
Executes tool calls against the live Amazon Bedrock AgentCore Gateway in ap-southeast-2
and captures genuine Cedar Policy DENY enforcement payloads.
"""
import sys
import json
import requests
import botocore.session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

GATEWAY_MCP_URL = "https://cedarshieldgateway-pgs4beuirv.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com/mcp"
REGION = "ap-southeast-2"
SERVICE = "bedrock-agentcore"

def call_agentcore_tool(tool_name: str, arguments: dict, caller_description: str):
    session = botocore.session.get_session()
    credentials = session.get_credentials().get_frozen_credentials()

    payload = {
        "jsonrpc": "2.0",
        "id": f"call-{tool_name}",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    body = json.dumps(payload)
    headers = {
        "Content-Type": "application/json",
        "Host": "cedarshieldgateway-pgs4beuirv.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com"
    }

    aws_request = AWSRequest(method="POST", url=GATEWAY_MCP_URL, data=body, headers=headers)
    SigV4Auth(credentials, SERVICE, REGION).add_auth(aws_request)

    print("\n" + "=" * 80)
    print(f" AGENT ACTION: Calling Tool '{tool_name}'")
    print(f" Context / Role: {caller_description}")
    print(f" Target Gateway: {GATEWAY_MCP_URL}")
    print(f" Input Arguments: {json.dumps(arguments)}")
    print("=" * 80)

    res = requests.post(GATEWAY_MCP_URL, headers=dict(aws_request.headers), data=body, timeout=10)
    resp_json = res.json()

    print(f" HTTP Status: {res.status_code}")
    print(f" Gateway Response Payload:\n{json.dumps(resp_json, indent=2)}")

    if "error" in resp_json:
        err = resp_json["error"]
        print(f" [DENIAL INTERCEPTED] Code: {err.get('code')} | Reason: {err.get('message')}")
    else:
        print(f" [ACTION PERMITTED] Tool executed successfully.")

    return resp_json

if __name__ == "__main__":
    print("Initializing Bedrock AgentCore MCP Handshake...")
    # Handshake
    s = botocore.session.get_session()
    c = s.get_credentials().get_frozen_credentials()
    init_req = AWSRequest(method="POST", url=GATEWAY_MCP_URL, data=json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"CedarShieldDemoAgent","version":"1.0.0"}}}), headers={"Content-Type":"application/json"})
    SigV4Auth(c, SERVICE, REGION).add_auth(init_req)
    requests.post(GATEWAY_MCP_URL, headers=dict(init_req.headers), data=init_req.body)
    print("MCP Handshake complete.\n")

    # Case 1: delete-resource by non-admin role (Deliberately triggers DENY)
    call_agentcore_tool(
        tool_name="delete-resource___delete_resource",
        arguments={"resource_id": "prod-financial-db-01"},
        caller_description="Support Agent (Role: support_agent) attempting to delete production database"
    )

    # Case 2: process-refund with excess amount ($2500)
    call_agentcore_tool(
        tool_name="process-refund___process_refund",
        arguments={"amount": 2500, "reason": "Disputed VIP charge"},
        caller_description="Finance Agent (Role: finance_agent) attempting unauthorized high-value refund ($2500 > $500 limit)"
    )

    # Case 3: read-record
    call_agentcore_tool(
        tool_name="read-record___read_record",
        arguments={"record_id": "rec_customer_9876"},
        caller_description="Support Agent reading record"
    )
