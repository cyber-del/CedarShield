import json
import threading
import urllib.request
import urllib.error
import boto3
from decimal import Decimal
from unittest.mock import patch
import pytest
from moto import mock_aws
import src.server as server
from src.server import (
    ThreadedHTTPServer,
    CedarShieldApiHandler,
    compute_kpis_from_items,
    canonical_hash_block,
)
from tests.unit.test_hash_chain import GENESIS_PREV_HASH

TABLE_NAME = "cedarshield-audit-log"
REGION = "ap-southeast-2"


@pytest.fixture
def mock_server_dynamodb():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "run_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "run_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def test_server(mock_server_dynamodb):
    # Patch the table in src.server
    with patch("src.server.table", mock_server_dynamodb):
        httpd = ThreadedHTTPServer(("127.0.0.1", 0), CedarShieldApiHandler)
        port = httpd.server_port
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = True
        thread.start()

        yield f"http://127.0.0.1:{port}"

        httpd.shutdown()
        httpd.server_close()


class TestServerApi:
    """
    Integration tests for CedarShield local server API endpoints.
    """

    def test_compute_kpis_from_items(self):
        sample_items = [
            {"principal": "FinanceAgent", "status": "APPROVED", "final_decision": "APPLIED"},
            {"principal": "SupportAgent", "status": "AWAITING_APPROVAL", "final_decision": "MANUAL_REVIEW"},
            {"principal": "FinanceAgent", "status": "APPROVED", "final_decision": "APPLIED"},
        ]
        kpis = compute_kpis_from_items(sample_items)
        assert kpis["policy_violations"] == 3
        assert kpis["auto_remediable"] == 2
        assert kpis["pending_approval"] == 1
        assert kpis["active_agents"] == 2

    def test_get_health_endpoint(self, test_server):
        url = f"{test_server}/api/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "HEALTHY"

    def test_get_audit_log_endpoint(self, test_server, mock_server_dynamodb):
        # Insert a genesis block into table
        block = {
            "run_id": "run_genesis",
            "sequence_number": "1",
            "status": "APPROVED",
            "action": "process-refund",
            "amount": Decimal("1000"),
            "prev_hash": GENESIS_PREV_HASH,
        }
        block["record_hash"] = canonical_hash_block(block)
        mock_server_dynamodb.put_item(Item=block)

        url = f"{test_server}/api/audit-log"
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "SUCCESS"
            assert len(data["runs"]) == 1
            assert data["runs"][0]["run_id"] == "run_genesis"
            assert "kpis" in data

    def test_trigger_denial_endpoint(self, test_server):
        url = f"{test_server}/api/trigger-denial"
        payload = json.dumps({
            "scenario": "vip_refund",
            "agent": "FinanceAgent",
            "amount": 2000,
        }).encode("utf-8")

        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "DENIAL_CAPTURED"
            assert "run_id" in data
            assert data.get("eventbridge_published") is True

    def test_approve_patch_endpoint(self, test_server, mock_server_dynamodb):
        # Seed an item needing approval
        b = {
            "run_id": "run_to_approve",
            "sequence_number": "1",
            "current_policy": "permit (...) when { context.amount <= 500 };",
            "patch": {"proposed_policy": "permit (...) when { context.amount <= 2500 };"},
            "prev_hash": GENESIS_PREV_HASH,
            "status": "AWAITING_APPROVAL",
        }
        b["record_hash"] = canonical_hash_block(b)
        mock_server_dynamodb.put_item(Item=b)

        url = f"{test_server}/api/approve"
        payload = json.dumps({
            "run_id": "run_to_approve",
            "reviewer": "security-reviewer@example.com",
            "signature": "valid-sig-token",
        }).encode("utf-8")

        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        with patch.object(server.control_client, "update_policy"):
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode("utf-8"))
                assert data["status"] == "APPROVED"
                assert "Policy successfully mutated" in data["message"]

    def test_verify_audit_chain_endpoint(self, test_server, mock_server_dynamodb):
        # Insert a valid chain of 2 blocks
        b1 = {
            "run_id": "chain_srv_1",
            "sequence_number": "1",
            "status": "APPROVED",
            "prev_hash": "0" * 64,
        }
        b1["record_hash"] = canonical_hash_block(b1)
        mock_server_dynamodb.put_item(Item=b1)

        b2 = {
            "run_id": "chain_srv_2",
            "sequence_number": "2",
            "status": "APPROVED",
            "prev_hash": b1["record_hash"],
        }
        b2["record_hash"] = canonical_hash_block(b2)
        mock_server_dynamodb.put_item(Item=b2)

        url = f"{test_server}/api/verify-audit-chain"
        req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["is_valid"] is True
            assert data["total_blocks"] == 2

    def test_simulate_abuse_endpoint(self, test_server, mock_server_dynamodb):
        # Insert an initial block with pre-patch policy
        b1 = {
            "run_id": "init_srv_policy",
            "sequence_number": "1",
            "current_policy": "permit (...) when { context.amount <= 500 };",
            "status": "APPROVED",
            "prev_hash": "0" * 64,
        }
        b1["record_hash"] = canonical_hash_block(b1)
        mock_server_dynamodb.put_item(Item=b1)

        # Trigger anomaly rollback with 3 near-ceiling calls
        url = f"{test_server}/api/simulate-abuse"
        payload = json.dumps({
            "amounts": [2450, 2480, 2490],
            "action": "process-refund"
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with patch.object(server.control_client, "update_policy"):
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode("utf-8"))
                assert data["status"] == "ROLLED_BACK"
                assert data["anomaly_detected"] is True
                assert data["rollback_executed"] is True

