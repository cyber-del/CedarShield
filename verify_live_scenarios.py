"""
CedarShield Live Verification: Both PERMIT and DENY Scenarios
Invokes Bedrock AgentCore Gateway with distinct assumed IAM roles:
1. Support Agent -> read_record (PERMIT / ALLOWED)
2. Support Agent -> delete_resource (DENIED - role mismatch)
3. Finance Agent -> process_refund ($250 <= $500) (PERMIT / ALLOWED)
4. Finance Agent -> process_refund ($2000 > $500) (DENIED - amount condition boundary)
"""
import sys
import json
import time
import requests
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

GATEWAY_MCP_URL = "https://cedarshieldgateway-pgs4beuirv.gateway.bedrock-agentcore.ap-southeast-2.amazonaws.com/mcp"
REGION = "ap-southeast-2"
SERVICE = "bedrock-agentcore"

sts = boto3.client("sts", region_name=REGION)

def get_assumed_credentials(role_arn: str, session_name: str):
    """Assumes the specified IAM role and returns frozen credentials."""
    resp = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name,
        DurationSeconds=900
    )
    c = resp["Credentials"]
    session = boto3.Session(
        aws_access_key_id=c["AccessKeyId"],
        aws_secret_access_key=c["SecretAccessKey"],
        aws_session_token=c["SessionToken"]
    )
    return session.get_credentials().get_frozen_credentials(), resp["AssumedRoleUser"]["Arn"]

def invoke_tool(tool_name: str, arguments: dict, role_arn: str, role_label: str):
    creds, caller_arn = get_assumed_credentials(role_arn, f"session-{tool_name[:8]}")

    # 1. MCP initialize handshake
    init_payload = {
        "jsonrpc": "2.0",
        "id": "init-1",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "CedarShieldDemoAgent", "version": "1.0.0"}
        }
    }
    init_body = json.dumps(init_payload)
    init_req = AWSRequest(method="POST", url=GATEWAY_MCP_URL, data=init_body, headers={"Content-Type": "application/json"})
    SigV4Auth(creds, SERVICE, REGION).add_auth(init_req)
    requests.post(GATEWAY_MCP_URL, headers=dict(init_req.headers), data=init_body, timeout=10)

    # 2. Invoke tools/call
    call_payload = {
        "jsonrpc": "2.0",
        "id": f"req-{tool_name}",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    call_body = json.dumps(call_payload)
    call_req = AWSRequest(method="POST", url=GATEWAY_MCP_URL, data=call_body, headers={"Content-Type": "application/json"})
    SigV4Auth(creds, SERVICE, REGION).add_auth(call_req)

    print("\n" + "=" * 80)
    print(f" [RUN] Tool: {tool_name}")
    print(f"  Role Label: {role_label}")
    print(f"  Caller ARN: {caller_arn}")
    print(f"  Arguments : {json.dumps(arguments)}")
    print("=" * 80)

    res = requests.post(GATEWAY_MCP_URL, headers=dict(call_req.headers), data=call_body, timeout=15)
    resp_json = res.json()
    print(f" HTTP Status: {res.status_code}")
    print(f" Response Payload:\n{json.dumps(resp_json, indent=2)}")

    if "result" in resp_json:
        print(f" >>> [DECISION: PERMIT (ALLOWED)] - Tool Executed Live on AWS Lambda!")
    elif "error" in resp_json:
        err = resp_json["error"]
        print(f" >>> [DECISION: DENIED (BLOCKED)] - Enforced by AgentCore Cedar Policy!")
        print(f"     Error Code   : {err.get('code')}")
        print(f"     Error Message: {err.get('message')}")

    return resp_json

if __name__ == "__main__":
    SUPPORT_ROLE = "arn:aws:iam::097935663941:role/CedarShield-SupportAgent-Role"
    FINANCE_ROLE = "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role"

    print("Executing Live Gateway Cedar Policy Scenarios...")
    time.sleep(2)

    # Scenario 1: Support Agent reading record -> PERMIT
    print("\n>>> Scenario 1: Expected PERMIT (Support Agent calls read-record)")
    invoke_tool(
        tool_name="read-record___read_record",
        arguments={"record_id": "rec_customer_001"},
        role_arn=SUPPORT_ROLE,
        role_label="Support Agent"
    )

    # Scenario 2: Support Agent attempting delete -> DENIED
    print("\n>>> Scenario 2: Expected DENY (Support Agent attempts delete-resource)")
    invoke_tool(
        tool_name="delete-resource___delete_resource",
        arguments={"resource_id": "prod-financial-db-01"},
        role_arn=SUPPORT_ROLE,
        role_label="Support Agent"
    )

    # Scenario 3: Finance Agent refund within limit ($250 <= $500) -> PERMIT
    print("\n>>> Scenario 3: Expected PERMIT (Finance Agent processes refund $250 <= $500)")
    invoke_tool(
        tool_name="process-refund___process_refund",
        arguments={"amount": 250, "reason": "Authorized customer refund"},
        role_arn=FINANCE_ROLE,
        role_label="Finance Agent"
    )

    # Scenario 4: Finance Agent refund over limit ($2000 > $500) -> DENIED
    print("\n>>> Scenario 4: Expected DENY (Finance Agent processes refund $2000 > $500 limit)")
    invoke_tool(
        tool_name="process-refund___process_refund",
        arguments={"amount": 2000, "reason": "High-value VIP refund attempt"},
        role_arn=FINANCE_ROLE,
        role_label="Finance Agent"
    )
