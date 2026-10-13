from unittest.mock import patch
import pytest
from src.anomaly_monitor import (
    evaluate_and_rollback,
    parse_call_timestamp,
    lambda_handler,
)

FAKE_NOW = 1700001000.0  # Reference epoch timestamp for deterministic clock testing


class TestAnomalyWatcherSlidingWindow:
    """
    Tests the sliding-window velocity detector in the anomaly monitor using a fake clock.
    Verifies that near-ceiling clustering triggers rollback only within the configured time window.
    """

    @pytest.fixture
    def mock_clients(self):
        with patch("src.anomaly_monitor.table") as mock_tbl, \
             patch("src.anomaly_monitor.control_client") as mock_ctrl:
            # Setup mock scan to return an audit record with a pre-patch baseline policy
            mock_tbl.scan.return_value = {
                "Items": [
                    {
                        "sequence_number": "1",
                        "run_id": "genesis-run",
                        "current_policy": "permit (...) when { context.amount <= 500 };",
                        "prev_hash": "0" * 64,
                        "record_hash": "a" * 64,
                        "action": "process-refund",
                    }
                ]
            }
            yield mock_tbl, mock_ctrl

    def test_three_near_ceiling_calls_in_three_minutes_triggers_anomaly(self, mock_clients):
        mock_tbl, mock_ctrl = mock_clients

        # 3 calls within last 3 minutes (180s) relative to FAKE_NOW
        recent_invocations = [
            {"amount": 2300, "timestamp": FAKE_NOW - 150},  # 2.5 mins ago
            {"amount": 2400, "timestamp": FAKE_NOW - 80},   # 1.3 mins ago
            {"amount": 2490, "timestamp": FAKE_NOW - 10},   # 10s ago
        ]

        res = evaluate_and_rollback(
            recent_invocations,
            now_timestamp=FAKE_NOW,
            window_seconds=180,
            ceiling=2500,
            threshold_ratio=0.90,
        )

        assert res["anomaly_detected"] is True
        assert res["rollback_executed"] is True
        assert "Suspicious clustering anomaly detected" in res["reason"]
        assert res["sequence_number"] == 2

        # Verify update_policy was invoked on control_client to revert policy
        mock_ctrl.update_policy.assert_called_once()
        # Verify rollback record put to DynamoDB table
        mock_tbl.put_item.assert_called_once()

    def test_calls_spaced_outside_window_do_not_trigger_anomaly(self, mock_clients):
        mock_tbl, mock_ctrl = mock_clients

        # 3 calls, but the first one happened 5 minutes ago (outside 180s window)
        recent_invocations = [
            {"amount": 2450, "timestamp": FAKE_NOW - 320},  # 5.3 mins ago (expired)
            {"amount": 2460, "timestamp": FAKE_NOW - 90},   # 1.5 mins ago
            {"amount": 2480, "timestamp": FAKE_NOW - 20},   # 20s ago
        ]

        res = evaluate_and_rollback(
            recent_invocations,
            now_timestamp=FAKE_NOW,
            window_seconds=180,
            ceiling=2500,
            threshold_ratio=0.90,
        )

        assert res["anomaly_detected"] is False
        assert res["rollback_executed"] is False
        mock_ctrl.update_policy.assert_not_called()

    def test_normal_volume_under_ninety_percent_ceiling_does_not_trigger(self, mock_clients):
        mock_tbl, mock_ctrl = mock_clients

        # 5 calls within the 3-minute window, but amounts are normal (< $2,250)
        recent_invocations = [
            {"amount": 500, "timestamp": FAKE_NOW - 120},
            {"amount": 1000, "timestamp": FAKE_NOW - 90},
            {"amount": 1500, "timestamp": FAKE_NOW - 60},
            {"amount": 2000, "timestamp": FAKE_NOW - 30},
            {"amount": 2200, "timestamp": FAKE_NOW - 10},  # Below $2,250
        ]

        res = evaluate_and_rollback(
            recent_invocations,
            now_timestamp=FAKE_NOW,
            window_seconds=180,
            ceiling=2500,
            threshold_ratio=0.90,
        )

        assert res["anomaly_detected"] is False
        assert res["rollback_executed"] is False
        mock_ctrl.update_policy.assert_not_called()

    def test_iso_timestamp_parsing_support(self):
        t_iso = "2026-10-12T12:00:00Z"
        parsed = parse_call_timestamp({"timestamp": t_iso}, default_time=0.0)
        assert parsed > 0.0

        t_epoch = 1700000000.5
        assert parse_call_timestamp({"timestamp": t_epoch}, default_time=0.0) == 1700000000.5

        assert parse_call_timestamp({}, default_time=123.4) == 123.4

    def test_lambda_handler_entrypoint(self, mock_clients):
        mock_tbl, mock_ctrl = mock_clients
        event = {
            "recent_invocations": [
                {"amount": 2350, "timestamp": FAKE_NOW - 100},
                {"amount": 2400, "timestamp": FAKE_NOW - 50},
                {"amount": 2480, "timestamp": FAKE_NOW - 10},
            ],
            "now_timestamp": FAKE_NOW,
            "window_seconds": 180,
        }

        resp = lambda_handler(event, None)
        assert resp["statusCode"] == 200
        import json
        body = json.loads(resp["body"])
        assert body["anomaly_detected"] is True
