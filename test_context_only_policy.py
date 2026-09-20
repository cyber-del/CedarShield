import boto3
import time

c = boto3.client('bedrock-agentcore-control', region_name='ap-southeast-2')
engine_id = 'CedarShieldPolicyEngine-2ivsrp1osh'
gateway_arn = 'arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv'
policy_id = 'ReadRecordPolicy-x9jjxu0t2g'

candidate_stmts = [
    f"""permit (
    principal,
    action == AgentCore::Action::"read-record",
    resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
    context has record_id
}};""",
    f"""permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"read-record",
    resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
    context has record_id
}};""",
    f"""permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"read-record",
    resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
    context has arguments
}};"""
]

for i, stmt in enumerate(candidate_stmts):
    print(f"\n--- Testing Candidate {i+1} ---")
    try:
        resp = c.update_policy(
            policyEngineId=engine_id,
            policyId=policy_id,
            definition={'cedar': {'statement': stmt}}
        )
        print("Update response status:", resp.get('status'))
        for _ in range(15):
            time.sleep(1)
            p = c.get_policy(policyEngineId=engine_id, policyId=policy_id)
            if p['status'] == 'ACTIVE':
                print(f"Candidate {i+1} became ACTIVE!")
                break
            if p['status'] == 'UPDATE_FAILED':
                print(f"Candidate {i+1} UPDATE_FAILED:", p.get('statusReasons'))
                break
    except Exception as e:
        print("Error:", e)
