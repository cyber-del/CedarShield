// ============================================================================
// CedarShield Cedar Policy Set
// Attached to Bedrock AgentCore Policy Engine: CedarShieldPolicyEngine-2ivsrp1osh
// Governs AgentCore Gateway: cedarshieldgateway-pgs4beuirv
// Enforcement Mode: ENFORCE
// ============================================================================

// Rule 1: Process Refund (FinanceAgent role only, capped at $500)
permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"process-refund",
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"
)
when {
    principal.id like "*FinanceAgent*" &&
    context has amount && context.amount <= 500
};

// Rule 2: Read Record (SupportAgent or FinanceAgent role)
permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"read-record",
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"
)
when {
    principal.id like "*SupportAgent*" ||
    principal.id like "*FinanceAgent*"
};

// Rule 3: Delete Resource (AdminAgent role only)
permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"delete-resource",
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"
)
when {
    principal.id like "*AdminAgent*"
};
