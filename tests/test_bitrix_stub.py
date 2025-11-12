"""Tests for Bitrix integration stub mode."""
import pytest
from app.integrations.bitrix import BitrixIntegration, BitrixMode
from app.config import settings


def test_bitrix_stub_mode():
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
    assert "raw" in response
    
    # Restore original mode
    settings.BITRIX_MODE = original_mode


def test_bitrix_stub_update_task():
    """Test updating task in stub mode."""
    original_mode = settings.BITRIX_MODE
    settings.BITRIX_MODE = "stub"
    
    integration = BitrixIntegration()
    external_id = "test_task_123"
    payload = {"title": "Updated Task"}
    
    response = integration.update_task(external_id, payload)
    
    assert response["ok"] is True
    assert response["external_id"] == external_id
    assert "raw" in response
    
    settings.BITRIX_MODE = original_mode


def test_bitrix_stub_get_task():
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

