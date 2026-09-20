import boto3
import time

c = boto3.client('bedrock-agentcore-control', region_name='ap-southeast-2')
engine_id = 'CedarShieldPolicyEngine-2ivsrp1osh'
gateway_arn = 'arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv'
policy_id = 'ReadRecordPolicy-x9jjxu0t2g'

candidate_attributes = [
    "principal.arn like \"*SupportAgent*\"",
    "principal.roleArn like \"*SupportAgent*\"",
    "principal.roleName like \"*SupportAgent*\"",
    "principal.name like \"*SupportAgent*\"",
    "principal.id like \"*SupportAgent*\"",
    "principal.entityId like \"*SupportAgent*\"",
    "principal.accountId == \"097935663941\"",
    "context.callerArn like \"*SupportAgent*\"",
]

for attr in candidate_attributes:
    stmt = f"""permit (
        principal is AgentCore::IamEntity,
        action == AgentCore::Action::"read-record",
        resource == AgentCore::Gateway::"{gateway_arn}"
    )
    when {{
        {attr}
    }};"""
    try:
        c.update_policy(
            policyEngineId=engine_id,
            policyId=policy_id,
            definition={'cedar': {'statement': stmt}}
        )
        print(f"ACCEPTED SYNTAX: {attr}", flush=True)
    except Exception as e:
        print(f"REJECTED SYNTAX: {attr} -> {str(e).splitlines()[0]}", flush=True)
    time.sleep(1)
