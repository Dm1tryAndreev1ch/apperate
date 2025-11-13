"""Tests for Bitrix integration stub mode."""
import pytest  # type: ignore[import]
from app.integrations.bitrix import BitrixIntegration, BitrixMode
from app.config import settings


def test_bitrix_stub_mode(db_session):
    """Test Bitrix integration in stub mode."""
    # Ensure stub mode
    original_mode = settings.BITRIX_MODE
    settings.BITRIX_MODE = "stub"
    
    integration = BitrixIntegration()
    assert integration.mode == BitrixMode.STUB
    
    # Test create_task in stub mode
    payload = {"title": "Test Task", "description": "Test"}
    response = integration.create_task(payload)
    
    assert response["ok"] is True
    assert "external_id" in response
    assert response["external_id"].startswith("stub_task_")
    assert response["raw"]["fields"]["TITLE"] == "Test Task"
    assert response["raw"]["fields"]["DESCRIPTION"] == "Test"
    
    # Restore original mode
    settings.BITRIX_MODE = original_mode


def test_bitrix_stub_update_task(db_session):
    """Test updating task in stub mode."""
    original_mode = settings.BITRIX_MODE
    settings.BITRIX_MODE = "stub"
    
    integration = BitrixIntegration()
    external_id = "test_task_123"
    payload = {"title": "Updated Task"}
    
    response = integration.update_task(external_id, payload)
    
    assert response["ok"] is True
    assert response["external_id"] == external_id
    assert response["raw"]["fields"]["TITLE"] == "Updated Task"
    
    settings.BITRIX_MODE = original_mode


def test_bitrix_stub_get_task(db_session):
    """Test getting task in stub mode."""
    original_mode = settings.BITRIX_MODE
    settings.BITRIX_MODE = "stub"
    
    integration = BitrixIntegration()
    external_id = "test_task_123"
    
    response = integration.get_task(external_id)
    
    assert response["ok"] is True
    assert response["external_id"] == external_id
    assert "raw" in response
    
    settings.BITRIX_MODE = original_mode


def test_bitrix_live_create_task_payload(monkeypatch, db_session):
    original_mode = settings.BITRIX_MODE
    original_base_url = settings.BITRIX_BASE_URL
    original_token = settings.BITRIX_ACCESS_TOKEN

    settings.BITRIX_MODE = "live"
    settings.BITRIX_BASE_URL = "https://example.bitrix24.com/rest/1/abc/"
    settings.BITRIX_ACCESS_TOKEN = None

    captured = {}

    class DummyResponse:
        def __init__(self):
            self._json = {"result": {"task": {"id": 98765}}}

        def raise_for_status(self):
            return None

        def json(self):
            return self._json

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def post(self, url, json, headers, timeout):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            captured["timeout"] = timeout
            return DummyResponse()

    monkeypatch.setattr("app.integrations.bitrix.httpx.Client", DummyClient)

    integration = BitrixIntegration()
    payload = {"title": "Live Task", "description": "Live description", "status": "PENDING"}
    response = integration.create_task(payload)

    assert response["ok"] is True
    assert response["external_id"] == "98765"

    assert captured["url"] == "https://example.bitrix24.com/rest/1/abc/tasks.task.add.json"
    assert captured["json"] == {
        "fields": {"TITLE": "Live Task", "DESCRIPTION": "Live description", "STATUS": 0}
    }
    assert captured["headers"] == {}
    assert captured["timeout"] == 30

    settings.BITRIX_MODE = original_mode
    settings.BITRIX_BASE_URL = original_base_url
    settings.BITRIX_ACCESS_TOKEN = original_token

