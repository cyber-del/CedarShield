import boto3
from decimal import Decimal
from unittest.mock import patch
import pytest
from moto import mock_aws
from src.anomaly_monitor import (
    evaluate_and_rollback,
    canonical_hash_block,
    find_previous_policy_from_audit_ledger,
)
from tests.unit.test_hash_chain import verify_chain, GENESIS_PREV_HASH

TABLE_NAME = "cedarshield-audit-log"
REGION = "ap-southeast-2"


@pytest.fixture
def mock_aws_environment():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "run_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "run_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


class TestAnomalyRollbackMoto:
    """
    Integration tests verifying dynamic anomaly rollback with Moto DynamoDB and
    mocked AgentCore control plane.
    """

    def test_dynamic_pre_patch_retrieval_and_rollback_execution(self, mock_aws_environment):
        table = mock_aws_environment

        # 1. Seed Block #1: Genesis Baseline ($500 ceiling)
        baseline_policy_str = (
            "permit (principal, action == 'process-refund', resource) when { context.amount <= 500 };"
        )
        b1 = {
            "run_id": "run_01_baseline",
            "sequence_number": "1",
            "action": "process-refund",
            "amount": Decimal("500"),
            "current_policy": baseline_policy_str,
            "status": "APPLIED",
            "timestamp": "2026-10-12T10:00:00Z",
            "prev_hash": GENESIS_PREV_HASH,
        }
        b1["record_hash"] = canonical_hash_block(b1)
        table.put_item(Item=b1)

        # 2. Seed Block #2: Patched Policy ($2,500 ceiling)
        patched_policy_str = (
            "permit (principal, action == 'process-refund', resource) when { context.amount <= 2500 };"
        )
        b2 = {
            "run_id": "run_02_patched",
            "sequence_number": "2",
            "action": "process-refund",
            "amount": Decimal("2000"),
            "current_policy": patched_policy_str,
            "status": "APPLIED",
            "timestamp": "2026-10-12T10:05:00Z",
            "prev_hash": b1["record_hash"],
        }
        b2["record_hash"] = canonical_hash_block(b2)
        table.put_item(Item=b2)

        # 3. Test find_previous_policy_from_audit_ledger resolves pre-patch policy
        with patch("src.anomaly_monitor.table", table):
            pre_policy, run_id, seq = find_previous_policy_from_audit_ledger("process-refund")
            assert "context.amount" in pre_policy

        # 4. Trigger near-ceiling anomaly with 3 calls in 3-minute window
        now_ts = 1700000000.0
        near_ceiling_invocations = [
            {"amount": 2400, "timestamp": now_ts - 100},
            {"amount": 2450, "timestamp": now_ts - 50},
            {"amount": 2490, "timestamp": now_ts - 10},
        ]

        with patch("src.anomaly_monitor.table", table), \
             patch("src.anomaly_monitor.control_client") as mock_ctrl:
            res = evaluate_and_rollback(
                near_ceiling_invocations,
                now_timestamp=now_ts,
                window_seconds=180,
                ceiling=2500,
                threshold_ratio=0.90,
            )

            assert res["anomaly_detected"] is True
            assert res["rollback_executed"] is True
            assert res["sequence_number"] == 3

            # Verify AgentCore Policy Engine update was called
            mock_ctrl.update_policy.assert_called_once()
            called_stmt = mock_ctrl.update_policy.call_args.kwargs["definition"]["cedar"]["statement"]
            assert called_stmt == pre_policy

        # 5. Verify the full 3-block chain in DynamoDB has intact cryptographic integrity
        all_blocks = table.scan().get("Items", [])
        assert len(all_blocks) == 3
        is_valid, msg, count = verify_chain(all_blocks)
        assert is_valid is True
        assert count == 3
        assert "verified" in msg.lower()
