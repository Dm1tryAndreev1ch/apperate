"""Tests for Bitrix alert service."""
import pytest
from uuid import uuid4

from app.services.bitrix_alert_service import bitrix_alert_service
from app.services.analytics_service import AlertDTO


@pytest.mark.asyncio
async def test_map_alert_to_bitrix_payload():
    """Test mapping alert to Bitrix payload."""
    alert = AlertDTO(
        check_instance_id=uuid4(),
        category="quality",
        severity="CRITICAL",
        message="Test critical issue",
        metadata={"key": "value"},
    )
    
    payload = bitrix_alert_service.build_bitrix_payload(alert)
    
    assert payload is not None
    assert "title" in payload
    assert "MantaQC" in payload["title"]
    assert alert.message in payload["title"] or alert.category in payload["title"]


def test_alert_deduplication():
    """Test that alerts are deduplicated correctly."""
    check_id = uuid4()
    alert1 = AlertDTO(
        check_instance_id=check_id,
        category="quality",
        severity="CRITICAL",
        message="Same issue",
        metadata={},
    )
    alert2 = AlertDTO(
        check_instance_id=check_id,
        category="quality",
        severity="CRITICAL",
        message="Same issue",
        metadata={},
    )
    
    # Both alerts should map to the same key
    key1 = bitrix_alert_service._hash_issue(alert1)
    key2 = bitrix_alert_service._hash_issue(alert2)
    
    assert key1 == key2

