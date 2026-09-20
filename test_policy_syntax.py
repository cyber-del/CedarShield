import boto3

c = boto3.client('bedrock-agentcore-control', region_name='ap-southeast-2')
engine_id = 'CedarShieldPolicyEngine-2ivsrp1osh'
policy_id = 'ReadRecordPolicy-x9jjxu0t2g'

tests = [
    'permit (principal, action, resource is AgentCore::Gateway);',
    'permit (principal, action, resource is AgentCore::Target);',
    'permit (principal, action, resource is AgentCore::Tool);',
    'permit (principal, action, resource is AgentCore::Action);',
    'permit (principal, action, resource);',
    'permit (principal is AgentCore::IamEntity, action, resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv");',
    'permit (principal is AgentCore::Principal, action, resource is AgentCore::Gateway);',
]

for stmt in tests:
    try:
        resp = c.update_policy(
            policyEngineId=engine_id,
            policyId=policy_id,
            definition={'cedar': {'statement': stmt}}
        )
        print("SUCCESS:", stmt)
    except Exception as e:
        print("FAIL:", stmt, "->", str(e).split("\n")[0])
