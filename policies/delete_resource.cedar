// Policy: Delete Resource
// Permits AdminAgent role ONLY to delete resources on AgentCore Gateway
permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"delete-resource",
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:ap-southeast-2:097935663941:gateway/cedarshieldgateway-pgs4beuirv"
)
when {
    principal.id like "*AdminAgent*"
};
