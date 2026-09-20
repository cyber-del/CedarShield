import boto3
import time

c = boto3.client('bedrock-agentcore-control', region_name='ap-southeast-2')
engine_id = 'CedarShieldPolicyEngine-2ivsrp1osh'
gateway_arn = 'arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv'
policy_id = 'ReadRecordPolicy-x9jjxu0t2g'

def wait_active():
    for _ in range(15):
        p = c.get_policy(policyEngineId=engine_id, policyId=policy_id)
        if p['status'] in ('ACTIVE', 'UPDATE_FAILED'):
            return
        time.sleep(1)

candidate_contexts = [
    "context has amount && context.amount <= 500",
    "context has arguments && context.arguments has amount && context.arguments.amount <= 500",
    "context has toolParameters && context.toolParameters has amount",
    "context has request && context.request has amount",
    "context has parameters && context.parameters has amount",
]

for ctx in candidate_contexts:
    wait_active()
    stmt = f"""permit (
        principal is AgentCore::IamEntity,
        action == AgentCore::Action::"process-refund",
        resource == AgentCore::Gateway::"{gateway_arn}"
    )
    when {{
        principal.arn like "*FinanceAgent*" &&
        {ctx}
    }};"""
    try:
        c.update_policy(
            policyEngineId=engine_id,
            policyId=policy_id,
            definition={'cedar': {'statement': stmt}}
        )
        print(f"ACCEPTED SYNTAX: {ctx}", flush=True)
    except Exception as e:
        print(f"REJECTED SYNTAX: {ctx} -> {str(e).splitlines()[0]}", flush=True)
