// Policy: Process Refund
// Permits FinanceAgent role to process refunds up to $500 on AgentCore Gateway
permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"process-refund",
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:123456789012:gateway/cedarshieldgateway-pgs4beuirv"
)
when {
    principal.id like "*FinanceAgent*" &&
    context has amount && context.amount <= 500
};
