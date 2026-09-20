import boto3
import time

c = boto3.client('bedrock-agentcore-control', region_name='ap-southeast-2')
engine_id = 'CedarShieldPolicyEngine-2ivsrp1osh'
policy_id = 'ReadRecordPolicy-x9jjxu0t2g'

def wait_active():
    for _ in range(15):
        p = c.get_policy(policyEngineId=engine_id, policyId=policy_id)
        if p['status'] == 'ACTIVE':
            return True
        time.sleep(1)
    return False

tests = [
    'permit (principal is AgentCore::IamEntity, action == AgentCore::Action::"read-record", resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv");',
    'permit (principal is AgentCore::IamEntity, action == AgentCore::Action::"read-record___read_record", resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv");',
    'permit (principal is AgentCore::IamEntity, action == AgentCore::Action::"read_record", resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv");',
]

for stmt in tests:
    wait_active()
    try:
        resp = c.update_policy(
            policyEngineId=engine_id,
            policyId=policy_id,
            definition={'cedar': {'statement': stmt}}
        )
        print("ACCEPTED:", stmt.split("action ==")[1].split(",")[0])
    except Exception as e:
        print("REJECTED:", str(e).split("\n")[0])
