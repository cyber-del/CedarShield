import boto3
import time

c = boto3.client('bedrock-agentcore-control', region_name='ap-southeast-2')
engine_id = 'CedarShieldPolicyEngine-2ivsrp1osh'
gateway_arn = 'arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv'

read_stmt = f"""permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"read-record",
    resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
    principal.id like "*SupportAgent*" ||
    principal.id like "*FinanceAgent*"
}};"""

print("Updating ReadRecordPolicy...")
resp = c.update_policy(
    policyEngineId=engine_id,
    policyId='ReadRecordPolicy-x9jjxu0t2g',
    definition={'cedar': {'statement': read_stmt}}
)
print("ReadRecordPolicy update initiated. Status:", resp.get('status'))

for _ in range(10):
    time.sleep(2)
    p = c.get_policy(policyEngineId=engine_id, policyId='ReadRecordPolicy-x9jjxu0t2g')
    print("Live status:", p['status'])
    if p['status'] == 'ACTIVE':
        break
