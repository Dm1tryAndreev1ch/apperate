"""Bitrix integration module."""
from datetime import datetime
from typing import Any, Dict
from urllib.parse import urljoin

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.integration import BitrixCallLog, BitrixMode
from tenacity import retry, stop_after_attempt, wait_exponential

# Create async engine for logging
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class BitrixIntegration:
    """Bitrix integration with stub and live modes."""

    def __init__(self):
        self.mode = BitrixMode(settings.BITRIX_MODE.lower())
        self.base_url = settings.BITRIX_BASE_URL.rstrip("/") if settings.BITRIX_BASE_URL else None
        self.access_token = settings.BITRIX_ACCESS_TOKEN

    async def _log_call(self, payload: Dict[str, Any], response: Dict[str, Any], mode: BitrixMode):
        """Log API call to database."""
        async with AsyncSessionLocal() as db:
            log_entry = BitrixCallLog(
                payload=payload,
                response=response,
                mode=mode,
            )
            db.add(log_entry)
            await db.commit()

    def _build_method_url(self, method: str) -> str:
        if not self.base_url:
            raise ValueError("Bitrix base URL not configured")

        base_with_slash = f"{self.base_url}/" if not self.base_url.endswith("/") else self.base_url
        return urljoin(base_with_slash, f"{method}.json")

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    @staticmethod
    def _prepare_task_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        if "title" in payload and payload["title"] is not None:
            fields["TITLE"] = payload["title"]
        if "description" in payload and payload["description"] is not None:
            fields["DESCRIPTION"] = payload["description"]
        if "deadline" in payload and payload["deadline"]:
            fields["DEADLINE"] = payload["deadline"]
        if "responsible_id" in payload and payload["responsible_id"]:
            fields["RESPONSIBLE_ID"] = payload["responsible_id"]
        if "creator_id" in payload and payload["creator_id"]:
            fields["CREATED_BY"] = payload["creator_id"]
        if "status" in payload and payload["status"]:
            status_map = {
                "PENDING": 0,
                "IN_PROGRESS": 2,
                "DONE": 5,
                "COMPLETED": 5,
            }
            bitrix_status = status_map.get(str(payload["status"]).upper())
            if bitrix_status is not None:
                fields["STATUS"] = bitrix_status
        if "tags" in payload and payload["tags"]:
            fields["TAGS"] = payload["tags"]
        return fields

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a task in Bitrix."""
        if self.mode == BitrixMode.STUB:
            # Stub mode - return mock response
            fields = self._prepare_task_fields(payload)
            response = {
                "ok": True,
                "external_id": f"stub_task_{datetime.utcnow().timestamp()}",
                "raw": {
                    "id": 12345,
                    "title": fields.get("TITLE") or payload.get("title", ""),
                    "fields": fields,
                },
            }
            # Log to database
            import asyncio
            asyncio.run(self._log_call({"fields": fields}, response, self.mode))
            return response
        else:
            # Live mode - make actual HTTP request
            return self._create_task_live(payload)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _create_task_live(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create task in Bitrix (live mode)."""
        headers = self._build_headers()
        url = self._build_method_url("tasks.task.add")
        request_payload = {"fields": self._prepare_task_fields(payload)}

        with httpx.Client() as client:
            response = client.post(url, json=request_payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

        result = {
            "ok": True,
            "external_id": str(data.get("result", {}).get("task", {}).get("id", "")),
            "raw": data,
        }

        import asyncio
        asyncio.run(self._log_call(request_payload, result, self.mode))
        return result

    def update_task(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update a task in Bitrix."""
        if self.mode == BitrixMode.STUB:
            fields = self._prepare_task_fields(payload)
            response = {
                "ok": True,
                "external_id": external_id,
                "raw": {"id": external_id, "updated": True, "fields": fields},
            }
            import asyncio
            asyncio.run(self._log_call({"taskId": external_id, "fields": fields}, response, self.mode))
            return response
        else:
            return self._update_task_live(external_id, payload)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _update_task_live(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update task in Bitrix (live mode)."""
        headers = self._build_headers()
        url = self._build_method_url("tasks.task.update")
        request_payload = {"taskId": external_id, "fields": self._prepare_task_fields(payload)}

        with httpx.Client() as client:
            response = client.post(url, json=request_payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

        result = {
            "ok": True,
            "external_id": external_id,
            "raw": data,
        }

        import asyncio
        asyncio.run(self._log_call(request_payload, result, self.mode))
        return result

    def get_task(self, external_id: str) -> Dict[str, Any]:
        """Get a task from Bitrix."""
        if self.mode == BitrixMode.STUB:
            response = {
                "ok": True,
                "external_id": external_id,
                "raw": {"id": external_id, "title": "Stub Task", "status": "pending"},
            }
            import asyncio
            asyncio.run(self._log_call({"external_id": external_id}, response, self.mode))
            return response
        else:
            return self._get_task_live(external_id)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _get_task_live(self, external_id: str) -> Dict[str, Any]:
        """Get task from Bitrix (live mode)."""
        headers = self._build_headers()
        url = self._build_method_url("tasks.task.get")
        request_payload = {"taskId": external_id}

        with httpx.Client() as client:
            response = client.post(url, json=request_payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

        result = {
            "ok": True,
            "external_id": external_id,
            "raw": data,
        }

        import asyncio
        asyncio.run(self._log_call(request_payload, result, self.mode))
        return result


# Global instance
bitrix_integration = BitrixIntegration()

