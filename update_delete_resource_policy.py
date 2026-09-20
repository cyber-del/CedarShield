import boto3
import time

c = boto3.client('bedrock-agentcore-control', region_name='ap-southeast-2')
engine_id = 'CedarShieldPolicyEngine-2ivsrp1osh'
gateway_arn = 'arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv'

stmt = f"""permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"delete-resource",
    resource == AgentCore::Gateway::"{gateway_arn}"
)
when {{
    principal.id like "arn:aws:iam::097935663941:role/*Admin*" ||
    principal.id like "arn:aws:sts::097935663941:assumed-role/*Admin*/*"
}};"""

print("Updating DeleteResourcePolicy...", flush=True)
c.update_policy(
    policyEngineId=engine_id,
    policyId='DeleteResourcePolicy-tclk9363hq',
    definition={'cedar': {'statement': stmt}}
)

for _ in range(15):
    time.sleep(1)
    p = c.get_policy(policyEngineId=engine_id, policyId='DeleteResourcePolicy-tclk9363hq')
    print("Status:", p['status'], flush=True)
    if p['status'] == 'ACTIVE':
        print("Successfully ACTIVE!")
        break
    if p['status'] == 'UPDATE_FAILED':
        print("Reasons:", p.get('statusReasons'), flush=True)
        break
