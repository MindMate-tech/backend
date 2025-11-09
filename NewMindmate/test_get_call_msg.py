import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from NewMindmate.get_all_call_history import app  # ✅ correct import

client = TestClient(app)

@pytest.fixture
def mock_beyondpresence_response():
    return [
        {"message": "Hello!", "sent_at": "2025-11-09T15:30:00Z", "sender": "user"},
        {"message": "Hi there!", "sent_at": "2025-11-09T15:30:02Z", "sender": "ai"}
    ]

@patch("NewMindmate.get_all_call_history.requests.get")
def test_get_call_messages_success(mock_get, mock_beyondpresence_response):
    mock_response = MagicMock()
    mock_response.json.return_value = mock_beyondpresence_response
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    response = client.get(
        "/calls/test-call/messages",
        headers={"x-api-key": "fake_api_key"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["call_id"] == "test-call"
    assert len(data["messages"]) == 2
