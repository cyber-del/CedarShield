import boto3
import time

c = boto3.client('bedrock-agentcore-control', region_name='ap-southeast-2')
engine_id = 'CedarShieldPolicyEngine-2ivsrp1osh'
gateway_id = 'cedarshieldgateway-pgs4beuirv'
gateway_arn = 'arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv'

tests = [
    f'permit (principal is AgentCore::IamEntity, action == AgentCore::Action::"read-record", resource == AgentCore::Gateway::"{gateway_id}") when {{ principal.id like "*097935663941*" }};',
    f'permit (principal is AgentCore::IamEntity, action == AgentCore::Action::"read-record", resource == AgentCore::Gateway::"{gateway_arn}") when {{ principal.id like "*097935663941*" }};',
]

for stmt in tests:
    try:
        c.update_policy(
            policyEngineId=engine_id,
            policyId='ReadRecordPolicy-x9jjxu0t2g',
            definition={'cedar': {'statement': stmt}}
        )
        print("ACCEPTED:", stmt.split("resource ==")[1].split(")")[0], flush=True)
    except Exception as e:
        print("REJECTED:", str(e).splitlines()[0], flush=True)
    time.sleep(2)
