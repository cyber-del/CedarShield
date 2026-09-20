import boto3, json

c = boto3.client("bedrock-agentcore-control", region_name="ap-southeast-2")
p = c.get_policy(policyEngineId="CedarShieldPolicyEngine-2ivsrp1osh", policyId="ProcessRefundPolicy-kryp2370fb")
live_stmt = p["definition"]["cedar"]["statement"]
patched_stmt = live_stmt.replace("context.amount <= 500", "context.amount <= 2500")

diff_lines = [
    "--- process_refund.cedar (current)",
    "+++ process_refund.cedar (proposed)",
    "@@ -1,11 +1,11 @@",
    " permit (",
    "     principal is AgentCore::IamEntity,",
    "     action == AgentCore::Action::\"process-refund\",",
    "     resource == AgentCore::Gateway::\"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv\"",
    " )",
    " when {",
    "     (",
    "         principal.id like \"arn:aws:iam::097935663941:role/*FinanceAgent*\" ||",
    "         principal.id like \"arn:aws:sts::097935663941:assumed-role/CedarShield-FinanceAgent-Role/*\"",
    "     ) &&",
    "-    context has amount && context.amount <= 500",
    "+    context has amount && context.amount <= 2500",
    " };"
]
diff_text = "\n".join(diff_lines)

sfn = boto3.client("stepfunctions", region_name="ap-southeast-2")
arn = "arn:aws:states:ap-southeast-2:097935663941:stateMachine:CedarShieldRemediationPipeline"
desc = sfn.describe_state_machine(stateMachineArn=arn)
defn = json.loads(desc["definition"])

defn["States"]["PatchState"]["Parameters"]["patch"] = {
    "diff": diff_text,
    "proposed_policy": patched_stmt,
    "change_summary": "Expanded refund threshold from 500 to 2500 for AgentCore::IamEntity FinanceAgent role while maintaining strict AgentCore::Action::\"process-refund\" scoping."
}

# Also ensure Adversarial tests use AgentCore Action and Role
defn["States"]["AdversarialTestGenState"]["Parameters"]["adversarial_tests"] = [
    {
        "id": "test_boundary_exact",
        "description": "Exact threshold boundary ($2,500 by FinanceAgent)",
        "principal": "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role",
        "action": "process-refund",
        "amount": 2500,
        "expected": "PERMIT"
    },
    {
        "id": "test_over_boundary",
        "description": "Over-boundary threshold ($2,501 by FinanceAgent)",
        "principal": "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role",
        "action": "process-refund",
        "amount": 2501,
        "expected": "DENY"
    },
    {
        "id": "test_role_spoofing",
        "description": "Role spoofing ($2,000 refund by SupportAgent)",
        "principal": "arn:aws:iam::097935663941:role/CedarShield-SupportAgent-Role",
        "action": "process-refund",
        "amount": 2000,
        "expected": "DENY"
    },
    {
        "id": "test_negative_amount",
        "description": "Negative amount boundary ($-50 by FinanceAgent)",
        "principal": "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role",
        "action": "process-refund",
        "amount": -50,
        "expected": "DENY"
    },
    {
        "id": "test_action_escalation",
        "description": "Privilege escalation (delete-resource by FinanceAgent)",
        "principal": "arn:aws:iam::097935663941:role/CedarShield-FinanceAgent-Role",
        "action": "delete-resource",
        "amount": 0,
        "expected": "DENY"
    }
]

sfn.update_state_machine(
    stateMachineArn=arn,
    definition=json.dumps(defn)
)
print("SUCCESS: Updated Step Functions state machine with live AgentCore schema!")
