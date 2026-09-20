import subprocess
import json
import time

tests = [
    ("amount", "context.amount <= 500"),
    ("arguments_amount", "context.arguments.amount <= 500"),
    ("params_amount", "context.params.amount <= 500"),
    ("request_amount", "context.request.amount <= 500"),
    ("payload_amount", "context.payload.amount <= 500"),
    ("raw_context", "context has amount && context.amount <= 500"),
]

aws_cli = "C:\\Program Files\\Amazon\\AWSCLIV2\\aws.exe"
engine_id = "CedarShieldPolicyEngine-2ivsrp1osh"
gateway_arn = "arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"

for name, condition in tests:
    stmt = f"""permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"process-refund",
    resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
    principal.id like "*finance*" &&
    {condition}
}};"""

    with open("temp_pol.json", "w") as f:
        json.dump({"cedar": {"statement": stmt}}, f)

    pname = f"TestPol{name}"
    cmd = [
        aws_cli, "bedrock-agentcore-control", "create-policy",
        "--policy-engine-id", engine_id,
        "--name", pname,
        "--enforcement-mode", "ACTIVE",
        "--definition", "file://temp_pol.json",
        "--region", "ap-southeast-2"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if "policyId" in res.stdout:
        pid = json.loads(res.stdout)["policyId"]
        time.sleep(2)
        # Check if ACTIVE or failed
        chk_cmd = [
            aws_cli, "bedrock-agentcore-control", "get-policy",
            "--policy-engine-id", engine_id,
            "--policy-id", pid,
            "--region", "ap-southeast-2"
        ]
        chk_res = subprocess.run(chk_cmd, capture_output=True, text=True)
        chk_json = json.loads(chk_res.stdout)
        status = chk_json.get("status")
        print(f"Condition '{condition}' -> Status: {status}")
        if status == "ACTIVE":
            print(f" FOUND WORKING SYNTAX: {condition}")
            # Keep or delete
            break
        else:
            print(f"   Reason: {chk_json.get('statusReasons')}")
            # Delete failed
            subprocess.run([aws_cli, "bedrock-agentcore-control", "delete-policy", "--policy-engine-id", engine_id, "--policy-id", pid, "--region", "ap-southeast-2"], capture_output=True)
    else:
        print(f"Condition '{condition}' creation failed: {res.stderr.strip()[:160]}")
