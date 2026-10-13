import json
import pytest
from unittest.mock import MagicMock, patch
from tests.conftest import load_lambda_module

generate_patch_mod = load_lambda_module("generate-patch")
validate_patch_guardrails = generate_patch_mod.validate_patch_guardrails
MAX_AUTONOMOUS_THRESHOLD = generate_patch_mod.MAX_AUTONOMOUS_THRESHOLD


class TestCedarGuardrails:
    """
    Tests static safety guardrails applied to candidate Cedar policy patches.
    """

    def test_guardrail_accepts_valid_scoped_policy(self):
        valid_policy = """
        permit (
            principal is AgentCore::IamEntity,
            action == AgentCore::Action::"process-refund",
            resource == AgentCore::Gateway::"sample-gateway"
        )
        when {
            principal.id like "*FinanceAgent*" &&
            context has amount && context.amount <= 2500
        };
        """
        is_safe, msg = validate_patch_guardrails(valid_policy, max_threshold=2500)
        assert is_safe is True
        assert "passed" in msg.lower()

    def test_guardrail_rejects_when_true_condition_stripping(self):
        unsafe_policy_1 = """
        permit (
            principal is AgentCore::IamEntity,
            action == AgentCore::Action::"process-refund",
            resource == AgentCore::Gateway::"sample-gateway"
        )
        when { true };
        """
        is_safe, msg = validate_patch_guardrails(unsafe_policy_1)
        assert is_safe is False
        assert "when { true }" in msg

        unsafe_policy_2 = "permit (principal, action, resource) when { True };"
        is_safe_2, msg_2 = validate_patch_guardrails(unsafe_policy_2)
        assert is_safe_2 is False

    def test_guardrail_rejects_unconditional_permit(self):
        unconditional_policy = """
        permit (
            principal is AgentCore::IamEntity,
            action == AgentCore::Action::"process-refund",
            resource == AgentCore::Gateway::"sample-gateway"
        );
        """
        is_safe, msg = validate_patch_guardrails(unconditional_policy)
        assert is_safe is False
        assert "unconditional" in msg.lower()

    def test_guardrail_rejects_boundary_exceeding_max_threshold(self):
        policy_exceeding_ceiling = """
        permit (
            principal is AgentCore::IamEntity,
            action == AgentCore::Action::"process-refund",
            resource == AgentCore::Gateway::"sample-gateway"
        )
        when {
            principal.id like "*FinanceAgent*" &&
            context has amount && context.amount <= 5000
        };
        """
        is_safe, msg = validate_patch_guardrails(policy_exceeding_ceiling, max_threshold=2500)
        assert is_safe is False
        assert "exceeds autonomous ceiling" in msg

    def test_guardrail_rejects_empty_or_malformed_input(self):
        assert validate_patch_guardrails("")[0] is False
        assert validate_patch_guardrails(None)[0] is False


class TestCeilingGuard:
    """
    Tests the $2,500 hard autonomous safety ceiling enforcement in GeneratePatch.
    """

    @pytest.fixture
    def base_event(self):
        return {
            "run_id": "test_run_ceiling_001",
            "principal": "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
            "action": "process-refund",
            "resource": "arn:aws:bedrock-agentcore:ap-southeast-2:123456789012:gateway/sample",
            "current_policy": "permit (...) when { context.amount <= 500 };",
            "diagnosis": {"root_cause": "Amount exceeds 500"},
            "retry_count": 0,
        }

    def test_ceiling_blocks_over_threshold_request(self, base_event):
        # Transaction requesting $5,000 (exceeds $2,500 ceiling)
        base_event["arguments"] = {"amount": 5000, "reason": "Enterprise refund"}

        with patch.object(generate_patch_mod, "bedrock_runtime") as mock_bedrock:
            res = generate_patch_mod.lambda_handler(base_event, None)

            # Bedrock must NOT be invoked when amount > ceiling
            mock_bedrock.invoke_model.assert_not_called()

            assert res.get("exceeds_max_autonomous_threshold") is True
            assert res.get("max_autonomous_threshold") == 2500
            assert "manual" in res.get("rejection_reason").lower()

    def test_ceiling_permits_under_or_equal_threshold_request(self, base_event):
        # Transaction requesting $2,000 (within $2,500 ceiling)
        base_event["arguments"] = {"amount": 2000, "reason": "VIP refund"}

        mock_claude_response = {
            "proposed_policy": """
            permit (
                principal is AgentCore::IamEntity,
                action == AgentCore::Action::"process-refund",
                resource == AgentCore::Gateway::"sample"
            )
            when {
                principal.id like "*FinanceAgent*" &&
                context has amount && context.amount <= 2500
            };
            """,
            "diff": "--- old\n+++ new\n+ context.amount <= 2500",
            "rationale": "Expanded cap safely to $2,500",
            "risk_assessment": {"risk_score": 10},
        }

        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps(
            {"content": [{"text": f"```json\n{json.dumps(mock_claude_response)}\n```"}]}
        ).encode("utf-8")

        mock_dynamo = MagicMock()

        with patch.object(generate_patch_mod.bedrock_runtime, "invoke_model", return_value={"body": mock_body}), \
             patch.object(generate_patch_mod.dynamodb, "Table", return_value=mock_dynamo):
            res = generate_patch_mod.lambda_handler(base_event, None)

            assert res.get("exceeds_max_autonomous_threshold") is not True
            assert "patch" in res
            assert res["patch"]["proposed_policy"] == mock_claude_response["proposed_policy"]

    def test_ceiling_handles_bedrock_generating_unsafe_when_true(self, base_event):
        # Bedrock attempts to return an unsafe condition stripping patch
        base_event["arguments"] = {"amount": 2000}

        unsafe_claude_response = {
            "proposed_policy": "permit (principal, action, resource) when { true };",
            "diff": "stripping all conditions",
        }

        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps(
            {"content": [{"text": json.dumps(unsafe_claude_response)}]}
        ).encode("utf-8")

        mock_dynamo = MagicMock()

        with patch.object(generate_patch_mod.bedrock_runtime, "invoke_model", return_value={"body": mock_body}), \
             patch.object(generate_patch_mod.dynamodb, "Table", return_value=mock_dynamo):
            res = generate_patch_mod.lambda_handler(base_event, None)

            # Unsafe patch must be discarded and replaced with safe fallback template
            assert "when { true }" not in res["patch"]["proposed_policy"]
            assert "context.amount <= 2500" in res["patch"]["proposed_policy"]
