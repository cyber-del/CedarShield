import pytest
from unittest.mock import patch
from tests.conftest import load_lambda_module

verify_patch_mod = load_lambda_module("verify-patch")
generate_adv_mod = load_lambda_module("generate-adversarial-tests")

SAMPLE_PATCHED_POLICY = """
permit (
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"process-refund",
    resource == AgentCore::Gateway::"cedarshieldgateway-sample"
)
when {
    principal.id like "*FinanceAgent*" &&
    context has amount && context.amount <= 2500
};
"""


class TestAdversarialBattery:
    """
    Parametrized evaluation of candidate Cedar policies across edge cases,
    boundary limits, and privilege escalation vectors.
    """

    @pytest.mark.parametrize(
        "test_name, principal, action, amount, expected_decision",
        [
            # Vector 1: Valid Baseline
            (
                "baseline_safe_transaction",
                "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "process-refund",
                100,
                "PERMIT",
            ),
            # Vector 2: Exact Requested Boundary
            (
                "boundary_exact_remediation",
                "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "process-refund",
                2000,
                "PERMIT",
            ),
            # Vector 3: Ceiling Boundary
            (
                "ceiling_exact_boundary",
                "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "process-refund",
                2500,
                "PERMIT",
            ),
            # Vector 4: Over-Boundary Violations
            (
                "over_boundary_threshold_plus_one",
                "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "process-refund",
                2501,
                "DENY",
            ),
            (
                "over_boundary_extreme_exfiltration",
                "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "process-refund",
                5000,
                "DENY",
            ),
            # Vector 5: Negative and Zero Amount Injections
            (
                "injection_negative_amount",
                "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "process-refund",
                -500,
                "DENY",
            ),
            (
                "injection_zero_amount",
                "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "process-refund",
                0,
                "DENY",
            ),
            # Vector 6: Privilege Escalation (Unauthorized Roles)
            (
                "privilege_escalation_support_role",
                "arn:aws:iam::123456789012:role/CedarShield-SupportAgent-Role",
                "process-refund",
                500,
                "DENY",
            ),
            (
                "privilege_escalation_untrusted_caller",
                "arn:aws:iam::123456789012:role/UntrustedLambdaCaller",
                "process-refund",
                100,
                "DENY",
            ),
            # Vector 7: Action Escalation
            (
                "action_escalation_delete_resource",
                "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "delete-resource",
                100,
                "DENY",
            ),
            (
                "action_escalation_read_record",
                "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "read-record",
                100,
                "DENY",
            ),
        ],
    )
    def test_evaluate_cedar_policy_adversarial_matrix(
        self, test_name, principal, action, amount, expected_decision
    ):
        actual = verify_patch_mod.evaluate_cedar_policy(
            policy_text=SAMPLE_PATCHED_POLICY,
            principal=principal,
            action=action,
            resource="cedarshieldgateway-sample",
            context_amount=amount,
        )
        assert actual == expected_decision, (
            f"Failed adversarial test '{test_name}': expected {expected_decision}, got {actual}"
        )

    def test_generate_adversarial_tests_fallback(self):
        event = {
            "run_id": "run_adv_001",
            "patch": {"target_limit": 2500, "proposed_policy": SAMPLE_PATCHED_POLICY},
            "arguments": {"amount": 2000},
            "retry_count": 0,
        }

        # Simulate Bedrock runtime throwing an exception
        with patch.object(
            generate_adv_mod.bedrock_runtime,
            "invoke_model",
            side_effect=RuntimeError("Bedrock unavailable"),
        ):
            res = generate_adv_mod.lambda_handler(event, None)
            tests = res.get("adversarial_tests", [])
            assert len(tests) >= 5

            categories = [t["category"] for t in tests]
            assert "BASELINE" in categories
            assert "BOUNDARY" in categories
            assert "PRIVILEGE_ESCALATION" in categories
            assert "INJECTION" in categories

    def test_verify_patch_lambda_handler_success_and_failure(self):
        adversarial_tests_passing = [
            {
                "id": "TC-01",
                "name": "Baseline",
                "category": "BASELINE",
                "principal": "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "amount": 100,
                "expected_decision": "PERMIT",
            },
            {
                "id": "TC-02",
                "name": "Over Boundary",
                "category": "BOUNDARY",
                "principal": "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "amount": 3000,
                "expected_decision": "DENY",
            },
        ]

        event = {
            "run_id": "run_verify_001",
            "patch": {"proposed_policy": SAMPLE_PATCHED_POLICY},
            "adversarial_tests": adversarial_tests_passing,
            "arguments": {},
            "action": "process-refund",
            "resource": "cedarshieldgateway-sample",
            "retry_count": 0,
        }

        res = verify_patch_mod.lambda_handler(event, None)
        assert res["verification"]["passed"] is True
        assert res["verification"]["passed_tests"] == 2
        assert res["verification"]["failed_tests"] == 0

        # Test with a failing test case (policy evaluates to DENY, but test expects PERMIT)
        adversarial_tests_failing = [
            {
                "id": "TC-FAIL",
                "name": "Failing Test",
                "category": "BOUNDARY",
                "principal": "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "amount": 5000,
                "expected_decision": "PERMIT",  # Policy will deny $5000, so this fails
            }
        ]
        event_failing = {
            "run_id": "run_verify_fail",
            "patch": {"proposed_policy": SAMPLE_PATCHED_POLICY},
            "adversarial_tests": adversarial_tests_failing,
            "arguments": {},
            "action": "process-refund",
            "resource": "cedarshieldgateway-sample",
            "retry_count": 0,
        }
        res_fail = verify_patch_mod.lambda_handler(event_failing, None)
        assert res_fail["verification"]["passed"] is False
        assert res_fail["verification"]["failed_tests"] == 1
