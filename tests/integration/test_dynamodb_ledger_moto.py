import boto3
from decimal import Decimal
import pytest
from moto import mock_aws
from src.anomaly_monitor import canonical_hash_block
from tests.unit.test_hash_chain import verify_chain, GENESIS_PREV_HASH

TABLE_NAME = "cedarshield-audit-log"
REGION = "ap-southeast-2"


@pytest.fixture
def mock_dynamodb_table():
    """
    Spins up an in-memory mock DynamoDB table matching the CedarShield audit log schema.
    """
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "run_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "run_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


class TestDynamoDBLedgerMoto:
    """
    Integration tests verifying DynamoDB operations against Moto,
    including tamper detection and cryptographic chain traversal.
    """

    def test_write_and_verify_ledger_chain(self, mock_dynamodb_table):
        # 1. Write Block #1 (Genesis)
        block_1 = {
            "run_id": "run_01_genesis",
            "sequence_number": "1",
            "action": "process-refund",
            "amount": Decimal("2000"),
            "status": "APPLIED",
            "timestamp": "2026-10-12T10:00:00Z",
            "prev_hash": GENESIS_PREV_HASH,
        }
        hash_1 = canonical_hash_block(block_1)
        block_1["record_hash"] = hash_1
        mock_dynamodb_table.put_item(Item=block_1)

        # 2. Write Block #2 (Escalation)
        block_2 = {
            "run_id": "run_02_escalation",
            "sequence_number": "2",
            "action": "process-refund",
            "amount": Decimal("5000"),
            "status": "MANUAL_REVIEW",
            "timestamp": "2026-10-12T10:05:00Z",
            "prev_hash": hash_1,
        }
        hash_2 = canonical_hash_block(block_2)
        block_2["record_hash"] = hash_2
        mock_dynamodb_table.put_item(Item=block_2)

        # 3. Scan and verify chain
        items = mock_dynamodb_table.scan().get("Items", [])
        is_valid, msg, count = verify_chain(items)
        assert is_valid is True
        assert count == 2

    def test_tampering_stored_record_in_dynamodb_fails_verification(self, mock_dynamodb_table):
        # Write 2 valid blocks
        b1 = {
            "run_id": "run_01",
            "sequence_number": "1",
            "amount": Decimal("1000"),
            "status": "APPLIED",
            "prev_hash": GENESIS_PREV_HASH,
        }
        b1["record_hash"] = canonical_hash_block(b1)
        mock_dynamodb_table.put_item(Item=b1)

        b2 = {
            "run_id": "run_02",
            "sequence_number": "2",
            "amount": Decimal("2000"),
            "status": "APPLIED",
            "prev_hash": b1["record_hash"],
        }
        b2["record_hash"] = canonical_hash_block(b2)
        mock_dynamodb_table.put_item(Item=b2)

        # Adversary uses DynamoDB UpdateItem to illicitly alter amount in Block 1
        mock_dynamodb_table.update_item(
            Key={"run_id": "run_01"},
            UpdateExpression="SET amount = :tampered",
            ExpressionAttributeValues={":tampered": Decimal("9999")},
        )

        items_after_tamper = mock_dynamodb_table.scan().get("Items", [])
        is_valid, msg, bad_seq = verify_chain(items_after_tamper)

        assert is_valid is False
        assert bad_seq == 1
        assert "Record hash mismatch at block #1" in msg
