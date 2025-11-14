"""Bitrix alert service for mapping report anomalies to Bitrix tickets."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.integrations.bitrix import bitrix_integration
from app.services.analytics_service import AlertDTO


class BitrixAlertService:
    """Service for creating Bitrix tickets from report alerts."""

    @staticmethod
    def _hash_issue(alert: AlertDTO) -> str:
        """Generate a unique hash for an issue to deduplicate."""
        key_parts = [
            alert.severity,
            alert.category,
            str(alert.check_instance_id) if alert.check_instance_id else "",
            str(alert.brigade_id) if alert.brigade_id else "",
            alert.message[:100],  # First 100 chars of message
        ]
        key = "|".join(key_parts)
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def build_bitrix_payload(
        alert: AlertDTO,
        *,
        check_instance_id: Optional[UUID] = None,
        report_id: Optional[UUID] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build Bitrix task payload from an alert."""
        # Build description
        description_parts = [
            f"**{alert.severity}**: {alert.message}",
            "",
            f"Категория: {alert.category}",
        ]

        if alert.check_instance_id:
            description_parts.append(f"ID обхода: {alert.check_instance_id}")
            if base_url:
                description_parts.append(f"Ссылка: {base_url}/checks/{alert.check_instance_id}")

        if alert.brigade_id:
            description_parts.append(f"ID бригады: {alert.brigade_id}")

        if alert.department_id:
            description_parts.append(f"Подразделение: {alert.department_id}")

        if alert.metadata:
            description_parts.append("")
            description_parts.append("Дополнительная информация:")
            for key, value in alert.metadata.items():
                if key != "bitrix_ticket_id":  # Exclude already stored ticket ID
                    description_parts.append(f"- {key}: {value}")

        description = "\n".join(description_parts)

        # Build title
        title = f"[MantaQC] {alert.category}: {alert.message[:50]}"

        # Determine responsible (can be configured via settings)
        responsible_id = None  # Will use default from Bitrix if not set

        # Build tags
        tags = ["MantaQC", alert.severity, alert.category]
        if alert.department_id:
            tags.append(alert.department_id)

        payload = {
            "title": title,
            "description": description,
            "tags": ", ".join(tags),
            "status": "PENDING",
        }

        if responsible_id:
            payload["responsible_id"] = responsible_id

        return payload

    @staticmethod
    def create_ticket_for_alert(
        alert: AlertDTO,
        *,
        check_instance_id: Optional[UUID] = None,
        report_id: Optional[UUID] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Bitrix ticket for an alert."""
        payload = BitrixAlertService.build_bitrix_payload(
            alert,
            check_instance_id=check_instance_id,
            report_id=report_id,
            base_url=base_url,
        )

        try:
            result = bitrix_integration.create_task(payload)
            return {
                "ok": result.get("ok", False),
                "external_id": result.get("external_id"),
                "hash": BitrixAlertService._hash_issue(alert),
                "raw": result.get("raw"),
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "hash": BitrixAlertService._hash_issue(alert),
            }

    @staticmethod
    def process_alerts(
        alerts: List[AlertDTO],
        *,
        check_instance_id: Optional[UUID] = None,
        report_id: Optional[UUID] = None,
        base_url: Optional[str] = None,
        deduplicate: bool = True,
    ) -> Dict[str, Dict[str, Any]]:
        """Process multiple alerts and create Bitrix tickets."""
        results: Dict[str, Dict[str, Any]] = {}
        seen_hashes: set[str] = set()

        for alert in alerts:
            if alert.severity not in ("WARNING", "ERROR", "CRITICAL"):
                continue  # Skip INFO-level alerts

            issue_hash = BitrixAlertService._hash_issue(alert)

            if deduplicate and issue_hash in seen_hashes:
                results[issue_hash] = {
                    "ok": False,
                    "skipped": True,
                    "reason": "duplicate",
                }
                continue

            seen_hashes.add(issue_hash)

            ticket_result = BitrixAlertService.create_ticket_for_alert(
                alert,
                check_instance_id=check_instance_id,
                report_id=report_id,
                base_url=base_url,
            )

            results[issue_hash] = ticket_result

            # Store ticket ID in alert metadata for later reference
            if ticket_result.get("ok") and ticket_result.get("external_id"):
                if alert.metadata is None:
                    alert.metadata = {}
                alert.metadata["bitrix_ticket_id"] = ticket_result["external_id"]

        return results


bitrix_alert_service = BitrixAlertService()

