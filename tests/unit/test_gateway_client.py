from unittest.mock import MagicMock, patch
import pytest
from src.agent_gateway_client import call_gateway_target


class TestAgentGatewayClient:
    """
    Unit tests for Bedrock AgentCore Gateway MCP SigV4 client.
    """

    @pytest.fixture
    def mock_boto_session(self):
        with patch("botocore.session.get_session") as mock_sess:
            mock_creds = MagicMock()
            mock_creds.get_frozen_credentials.return_value = MagicMock(
                access_key="test_ak", secret_key="test_sk", token="test_tok"
            )
            mock_sess.return_value.get_credentials.return_value = mock_creds
            yield mock_sess

    def test_call_gateway_target_success_json(self, mock_boto_session):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"status": "SUCCESS", "record_id": "cust_1001"}

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = call_gateway_target(
                target_name="read-record",
                payload={"record_id": "cust_1001"},
                caller_label="Finance Agent",
            )

            assert mock_post.called
            called_args, called_kwargs = mock_post.call_args
            assert "read-record" in called_args[0]
            assert "Authorization" in called_kwargs["headers"]
            assert result == {"status": "SUCCESS", "record_id": "cust_1001"}

    def test_call_gateway_target_raw_denial_fallback(self, mock_boto_session):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.json.side_effect = ValueError("Non-JSON denial response")
        mock_response.text = "Denied by Cedar Policy Engine: -32002"

        with patch("requests.post", return_value=mock_response):
            result = call_gateway_target(
                target_name="delete-resource",
                payload={"resource_id": "prod-01"},
                caller_label="Support Agent",
            )

            assert result["status_code"] == 403
            assert "-32002" in result["raw"]
