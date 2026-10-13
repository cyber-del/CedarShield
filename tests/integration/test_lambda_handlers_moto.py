import json
import boto3
from unittest.mock import MagicMock, patch
import pytest
from moto import mock_aws
from tests.conftest import load_lambda_module

diagnose_mod = load_lambda_module("diagnose-denial")
generate_patch_mod = load_lambda_module("generate-patch")
generate_adv_mod = load_lambda_module("generate-adversarial-tests")
verify_patch_mod = load_lambda_module("verify-patch")
await_appr_mod = load_lambda_module("await-approval-handler")
approve_mod = load_lambda_module("api-approve")
reject_mod = load_lambda_module("api-reject")
trigger_mod = load_lambda_module("api-trigger-denial")
audit_mod = load_lambda_module("api-audit-log")
tool_refund_mod = load_lambda_module("tool-process-refund")
tool_read_mod = load_lambda_module("tool-read-record")
tool_delete_mod = load_lambda_module("tool-delete-resource")

TABLE_NAME = "cedarshield-audit-log"
REGION = "ap-southeast-2"


@pytest.fixture
def mock_dynamodb():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        sfn = boto3.client("stepfunctions", region_name=REGION)
        events = boto3.client("events", region_name=REGION)
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "run_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "run_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # Point imported Lambda module clients to the active Moto instance
        diagnose_mod.dynamodb = dynamodb
        generate_patch_mod.dynamodb = dynamodb
        generate_adv_mod.dynamodb = dynamodb
        verify_patch_mod.dynamodb = dynamodb
        await_appr_mod.dynamodb = dynamodb
        approve_mod.dynamodb = dynamodb
        approve_mod.sfn = sfn
        reject_mod.dynamodb = dynamodb
        reject_mod.sfn = sfn
        trigger_mod.dynamodb = dynamodb
        trigger_mod.events_client = events
        trigger_mod.sfn_client = sfn
        audit_mod.dynamodb = dynamodb
        audit_mod.table = table

        yield table


class TestLambdaHandlersMoto:
    """
    End-to-end integration tests of serverless Lambda handlers backed by Moto DynamoDB and Step Functions.
    """

    def test_pipeline_execution_flow(self, mock_dynamodb):
        run_id = "test_run_e2e_moto"

        # Initialize DynamoDB record
        mock_dynamodb.put_item(
            Item={
                "run_id": run_id,
                "status": "DENIED",
                "principal": "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "action": "process-refund",
                "resource": "cedarshieldgateway-sample",
                "amount": 2000,
            }
        )

        # Stage 1: Diagnose Denial
        diag_event = {
            "detail": {
                "run_id": run_id,
                "principal": "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
                "action": "process-refund",
                "resource": "cedarshieldgateway-sample",
                "arguments": {"amount": 2000},
                "current_policy": "permit (...) when { context.amount <= 500 };",
            }
        }

        mock_diag_response = {
            "root_cause": "Requested refund of $2000 exceeds $500 condition.",
            "failing_conditions": ["context.amount <= 500"],
            "confidence_score": 0.99,
        }
        mock_body_1 = MagicMock()
        mock_body_1.read.return_value = json.dumps(
            {"content": [{"text": json.dumps(mock_diag_response)}]}
        ).encode("utf-8")

        with patch.object(diagnose_mod.bedrock_runtime, "invoke_model", return_value={"body": mock_body_1}):
            diag_res = diagnose_mod.lambda_handler(diag_event, None)
            assert diag_res["diagnosis"]["confidence_score"] == 0.99

        # Stage 2: Generate Patch
        patch_event = {
            "run_id": run_id,
            "principal": diag_res["principal"],
            "action": diag_res["action"],
            "resource": diag_res["resource"],
            "arguments": {"amount": 2000},
            "current_policy": diag_res["current_policy"],
            "diagnosis": diag_res["diagnosis"],
            "retry_count": 0,
        }

        mock_patch_response = {
            "proposed_policy": """
            permit (
                principal is AgentCore::IamEntity,
                action == AgentCore::Action::"process-refund",
                resource == AgentCore::Gateway::"cedarshieldgateway-sample"
            )
            when {
                principal.id like "*FinanceAgent*" &&
                context has amount && context.amount <= 2500
            };
            """,
            "diff": "--- old\n+++ new\n+ context.amount <= 2500",
            "target_limit": 2500,
        }
        mock_body_2 = MagicMock()
        mock_body_2.read.return_value = json.dumps(
            {"content": [{"text": json.dumps(mock_patch_response)}]}
        ).encode("utf-8")

        with patch.object(generate_patch_mod.bedrock_runtime, "invoke_model", return_value={"body": mock_body_2}):
            patch_res = generate_patch_mod.lambda_handler(patch_event, None)
            assert "patch" in patch_res
            assert patch_res["patch"]["target_limit"] == 2500

        # Stage 3: Generate Adversarial Tests
        adv_event = {
            "run_id": run_id,
            "patch": patch_res["patch"],
            "arguments": {"amount": 2000},
            "retry_count": 0,
        }
        with patch.object(generate_adv_mod.bedrock_runtime, "invoke_model", side_effect=RuntimeError("fallback")):
            adv_res = generate_adv_mod.lambda_handler(adv_event, None)
            tests = adv_res["adversarial_tests"]
            assert len(tests) >= 5

        # Stage 4: Verify Patch
        verify_event = {
            "run_id": run_id,
            "patch": patch_res["patch"],
            "adversarial_tests": tests,
            "action": "process-refund",
            "resource": "cedarshieldgateway-sample",
            "arguments": {"amount": 2000},
            "retry_count": 0,
        }
        verify_res = verify_patch_mod.lambda_handler(verify_event, None)
        assert verify_res["verification"]["passed"] is True

        # Stage 5: Await Approval Handler
        await_event = {
            "token": "sfn_task_token_xyz_123",
            "execution_id": "arn:aws:states:sfn:exec:123",
            "pipeline_data": {"run_id": run_id},
        }
        await_res = await_appr_mod.lambda_handler(await_event, None)
        assert await_res["status"] == "AWAITING_APPROVAL"

        # Verify DynamoDB was updated with task token
        stored_item = mock_dynamodb.get_item(Key={"run_id": run_id})["Item"]
        assert stored_item["task_token"] == "sfn_task_token_xyz_123"
        assert stored_item["status"] == "AWAITING_APPROVAL"

        # Stage 6: Approve Patch via API
        approve_event = {
            "body": json.dumps({
                "run_id": run_id,
                "approver_identity": "security-lead@example.com",
            })
        }
        with patch.object(approve_mod.sfn, "send_task_success") as mock_send_success, \
             patch.object(approve_mod, "get_agentcore_client") as mock_agentcore:
            mock_ctrl = MagicMock()
            mock_agentcore.return_value = mock_ctrl
            appr_res = approve_mod.lambda_handler(approve_event, None)
            assert appr_res["statusCode"] == 200
            assert mock_send_success.call_count == 1
            call_kwargs = mock_send_success.call_args.kwargs
            assert call_kwargs["taskToken"] == "sfn_task_token_xyz_123"
            assert "APPROVED" in call_kwargs["output"]

        # Confirm final record status in DynamoDB
        final_item = mock_dynamodb.get_item(Key={"run_id": run_id})["Item"]
        assert final_item["status"] == "APPROVED"
        assert final_item["approver_identity"] == "security-lead@example.com"

    def test_tool_lambdas(self):
        # Test tool-process-refund
        ref_res = tool_refund_mod.lambda_handler({"amount": 150}, None)
        assert ref_res["status"] == "SUCCESS"
        assert ref_res["amount"] == 150

        # Test tool-read-record
        read_res = tool_read_mod.lambda_handler({"record_id": "rec_001"}, None)
        assert read_res["status"] == "SUCCESS"
        assert read_res["record_id"] == "rec_001"

        # Test tool-delete-resource
        del_res = tool_delete_mod.lambda_handler({"resource_id": "res_001"}, None)
        assert del_res["status"] == "SUCCESS"
        assert del_res["resource_id"] == "res_001"

    def test_api_reject_endpoints(self, mock_dynamodb):
        # 1. Missing run_id -> 400
        res_400 = reject_mod.lambda_handler({"body": json.dumps({})}, None)
        assert res_400["statusCode"] == 400
        assert "Missing required field" in res_400["body"]

        # 2. Non-existent run_id -> 404
        res_404 = reject_mod.lambda_handler({"body": json.dumps({"run_id": "missing_run"})}, None)
        assert res_404["statusCode"] == 404
        assert "not found" in res_404["body"]

        # 3. Successful rejection with Task Token & JWT Authorizer Claims
        run_id = "run_to_reject_123"
        mock_dynamodb.put_item(
            Item={
                "run_id": run_id,
                "status": "AWAITING_APPROVAL",
                "task_token": "token_reject_abc",
            }
        )

        event = {
            "body": json.dumps({
                "run_id": run_id,
                "reason": "Security risk: requested amount too high",
            }),
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "email": "lead_auditor@corp.io",
                            "sub": "user_sub_888",
                        }
                    }
                }
            }
        }

        with patch.object(reject_mod.sfn, "send_task_failure") as mock_fail:
            res = reject_mod.lambda_handler(event, None)
            assert res["statusCode"] == 200
            body = json.loads(res["body"])
            assert body["decision"] == "REJECTED"
            assert "lead_auditor@corp.io" in body["approver_identity"]
            mock_fail.assert_called_once_with(
                taskToken="token_reject_abc",
                error="HumanReviewerRejected",
                cause="Security risk: requested amount too high",
            )

        # Check DB update
        item = mock_dynamodb.get_item(Key={"run_id": run_id})["Item"]
        assert item["status"] == "REJECTED"
        assert item["rejection_reason"] == "Security risk: requested amount too high"
        assert "lead_auditor@corp.io" in item["approver_identity"]

    def test_api_approve_edge_cases(self, mock_dynamodb):
        # 1. Missing run_id -> 400
        res_400 = approve_mod.lambda_handler({"body": json.dumps({})}, None)
        assert res_400["statusCode"] == 400

        # 2. Nonexistent run_id -> 404
        res_404 = approve_mod.lambda_handler({"body": json.dumps({"run_id": "nonexistent_run"})}, None)
        assert res_404["statusCode"] == 404

        # 3. Successful approval with JWT authorizer claims
        run_id = "run_to_approve_jwt"
        mock_dynamodb.put_item(
            Item={
                "run_id": run_id,
                "status": "AWAITING_APPROVAL",
                "task_token": "token_approve_jwt",
                "patch": {"proposed_policy": "permit(principal, action, resource);"},
            }
        )

        event = {
            "body": json.dumps({"run_id": run_id}),
            "requestContext": {
                "authorizer": {
                    "jwt": {
                        "claims": {
                            "email": "ciso@company.com",
                            "sub": "ciso_sub_777",
                        }
                    }
                }
            }
        }

        with patch.object(approve_mod.sfn, "send_task_success") as mock_succ, \
             patch.object(approve_mod, "get_agentcore_client") as mock_client:
            mock_ctrl = MagicMock()
            mock_client.return_value = mock_ctrl
            res = approve_mod.lambda_handler(event, None)
            assert res["statusCode"] == 200
            body = json.loads(res["body"])
            assert body["decision"] == "APPROVED"
            assert "ciso@company.com (sub: ciso_sub_777)" in body["approver_identity"]
            mock_succ.assert_called_once()
            mock_ctrl.update_policy.assert_called_once()

    def test_api_trigger_denial_flow(self, mock_dynamodb):
        run_id = "run_trigger_moto_test"
        event = {
            "body": json.dumps({
                "run_id": run_id,
                "amount": 2200,
                "reason": "Test high value denial",
            })
        }

        with patch.object(trigger_mod.sfn_client, "start_execution") as mock_start_exec:
            mock_start_exec.return_value = {"executionArn": "arn:aws:states:exec:123"}
            trigger_mod.STATE_MACHINE_ARN = "arn:aws:states:sm:test"

            res = trigger_mod.lambda_handler(event, None)
            assert res["statusCode"] == 200
            body = json.loads(res["body"])
            assert body["status"] == "DENIAL_CAPTURED"
            assert body["run_id"] == run_id

        # Verify DynamoDB record was created
        item = mock_dynamodb.get_item(Key={"run_id": run_id})["Item"]
        assert item["status"] == "DENIED"
        assert item["run_id"] == run_id

    def test_api_audit_log_endpoints(self, mock_dynamodb):
        # Health check route
        health_evt = {
            "rawPath": "/api/health",
            "requestContext": {"http": {"method": "GET"}},
        }
        res_h = audit_mod.lambda_handler(health_evt, None)
        assert res_h["statusCode"] == 200
        assert json.loads(res_h["body"])["status"] == "HEALTHY"

        # KPIs route
        kpi_evt = {
            "rawPath": "/api/kpis",
            "requestContext": {"http": {"method": "GET"}},
        }
        res_k = audit_mod.lambda_handler(kpi_evt, None)
        assert res_k["statusCode"] == 200
        assert "kpis" in json.loads(res_k["body"])

        # Audit log route
        # Seed 2 hash-chained items in the table
        item1 = {
            "run_id": "chain_block_1",
            "sequence_number": "1",
            "timestamp": "2026-09-20T10:00:00Z",
            "prev_hash": "0" * 64,
            "status": "APPROVED",
        }
        h1 = audit_mod.canonical_hash_block(item1)
        item1["record_hash"] = h1
        mock_dynamodb.put_item(Item=item1)

        item2 = {
            "run_id": "chain_block_2",
            "sequence_number": "2",
            "timestamp": "2026-09-20T10:05:00Z",
            "prev_hash": h1,
            "status": "APPROVED",
        }
        h2 = audit_mod.canonical_hash_block(item2)
        item2["record_hash"] = h2
        mock_dynamodb.put_item(Item=item2)

        log_evt = {
            "rawPath": "/api/audit-log",
            "requestContext": {"http": {"method": "GET"}},
        }
        res_l = audit_mod.lambda_handler(log_evt, None)
        assert res_l["statusCode"] == 200
        log_body = json.loads(res_l["body"])
        assert log_body["count"] == 2

        # Verify audit chain route
        verify_evt = {
            "rawPath": "/api/verify-audit-chain",
            "requestContext": {"http": {"method": "POST"}},
        }
        res_v = audit_mod.lambda_handler(verify_evt, None)
        assert res_v["statusCode"] == 200
        v_body = json.loads(res_v["body"])
        assert v_body["is_valid"] is True
        assert v_body["total_blocks"] == 2

        # Simulate abuse route - Healthy case
        abuse_healthy = {
            "rawPath": "/api/simulate-abuse",
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"amounts": [500, 600]}),
        }
        res_ah = audit_mod.lambda_handler(abuse_healthy, None)
        assert res_ah["statusCode"] == 200
        assert json.loads(res_ah["body"])["status"] == "HEALTHY"

        # Simulate abuse route - Anomaly rollback case
        item3 = {
            "run_id": "chain_block_3",
            "sequence_number": "3",
            "timestamp": "2026-09-20T10:10:00Z",
            "prev_hash": h2,
            "current_policy": "permit (...) when { context.amount <= 500 };",
            "status": "APPROVED",
        }
        h3 = audit_mod.canonical_hash_block(item3)
        item3["record_hash"] = h3
        mock_dynamodb.put_item(Item=item3)

        abuse_anomaly = {
            "rawPath": "/api/simulate-abuse",
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"amounts": [2450, 2480, 2490], "action": "process-refund"}),
        }
        with patch.object(audit_mod.control_client, "update_policy"):
            res_aa = audit_mod.lambda_handler(abuse_anomaly, None)
            assert res_aa["statusCode"] == 200
            a_body = json.loads(res_aa["body"])
            assert a_body["status"] == "ROLLED_BACK"
            assert a_body["anomaly_detected"] is True
            assert a_body["rollback_executed"] is True


