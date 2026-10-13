import json
import boto3
import pytest
from moto import mock_aws

REGION = "ap-southeast-2"


class TestEventBridgeMoto:
    """
    Integration tests for EventBridge event bus creation, rule configuration,
    and event publishing for policy denials.
    """

    @pytest.fixture
    def events_client(self):
        with mock_aws():
            client = boto3.client("events", region_name=REGION)
            yield client

    def test_publish_policy_denial_event(self, events_client):
        # 1. Create EventBridge rule for policy denials
        rule_name = "CedarShield-PolicyDenied-Rule"
        event_pattern = {
            "source": ["bedrock-agentcore.gateway"],
            "detail-type": ["CedarShield.PolicyDenied"],
        }
        events_client.put_rule(
            Name=rule_name,
            EventPattern=json.dumps(event_pattern),
            State="ENABLED",
            Description="Routes AgentCore Cedar denials to Step Functions remediation",
        )

        # 2. Put policy denial event
        payload = {
            "run_id": "run_eb_denial_001",
            "principal": "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
            "action": "process-refund",
            "resource": "arn:aws:bedrock-agentcore:ap-southeast-2:123456789012:gateway/sample",
            "arguments": {"amount": 2000, "reason": "VIP refund attempt"},
            "error_code": -32002,
            "error_message": "Unauthorized by active Cedar policy",
        }

        resp = events_client.put_events(
            Entries=[
                {
                    "Source": "bedrock-agentcore.gateway",
                    "DetailType": "CedarShield.PolicyDenied",
                    "Detail": json.dumps(payload),
                    "EventBusName": "default",
                }
            ]
        )

        assert resp["FailedEntryCount"] == 0
        assert len(resp["Entries"]) == 1
        assert "EventId" in resp["Entries"][0]

    def test_scheduled_anomaly_watcher_rule(self, events_client):
        # Create scheduled rule that fires the anomaly monitor every 2 minutes
        rule_name = "CedarShield-AnomalyWatcher-Schedule"
        rule_resp = events_client.put_rule(
            Name=rule_name,
            ScheduleExpression="rate(2 minutes)",
            State="ENABLED",
            Description="Periodic anomaly evaluation across agent invocations",
        )
        assert "RuleArn" in rule_resp
