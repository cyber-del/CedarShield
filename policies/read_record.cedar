// Policy: Read Record
// Permits SupportAgent or FinanceAgent to read records on AgentCore Gateway
permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"read-record",
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:123456789012:gateway/cedarshieldgateway-pgs4beuirv"
)
when {
    principal.id like "*SupportAgent*" ||
    principal.id like "*FinanceAgent*"
};
