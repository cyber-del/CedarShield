import boto3
import time
import json

c = boto3.client('bedrock-agentcore-control', region_name='ap-southeast-2')
engine_id = 'CedarShieldPolicyEngine-2ivsrp1osh'
gateway_arn = 'arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv'

policies = [
    {
        "id": "ReadRecordPolicy-x9jjxu0t2g",
        "name": "ReadRecordPolicy",
        "statement": f"""permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"read-record",
    resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
    principal.roleName like "*SupportAgent*" ||
    principal.roleName like "*FinanceAgent*" ||
    principal.arn like "*SupportAgent*" ||
    principal.arn like "*FinanceAgent*"
}};"""
    },
    {
        "id": "ProcessRefundPolicy-kryp2370fb",
        "name": "ProcessRefundPolicy",
        "statement": f"""permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"process-refund",
    resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
    (principal.roleName like "*FinanceAgent*" || principal.arn like "*FinanceAgent*") &&
    context has amount && context.amount <= 500
}};"""
    },
    {
        "id": "DeleteResourcePolicy-tclk9363hq",
        "name": "DeleteResourcePolicy",
        "statement": f"""permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"delete-resource",
    resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
    principal.roleName like "*Admin*" || principal.arn like "*admin*"
}};"""
    }
]

for pol in policies:
    print(f"Deploying {pol['name']} ({pol['id']})...", flush=True)
    c.update_policy(
        policyEngineId=engine_id,
        policyId=pol['id'],
        definition={'cedar': {'statement': pol['statement']}}
    )
    for _ in range(20):
        time.sleep(1)
        p = c.get_policy(policyEngineId=engine_id, policyId=pol['id'])
        print(f"  Status: {p['status']}", flush=True)
        if p['status'] == 'ACTIVE':
            break
        if p['status'] == 'UPDATE_FAILED':
            print("  FAILED reasons:", p.get('statusReasons'), flush=True)
            break

print("\n--- All Policies Updated. Verifying Final Status ---", flush=True)
all_pols = c.list_policies(policyEngineId=engine_id)
for p in all_pols['policies']:
    print(f"Policy: {p['name']} | Status: {p['status']} | ID: {p['policyId']}")
