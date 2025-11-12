"""Bitrix integration module."""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from datetime import datetime
import httpx
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
        self.base_url = settings.BITRIX_BASE_URL
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

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a task in Bitrix."""
        if self.mode == BitrixMode.STUB:
            # Stub mode - return mock response
            response = {
                "ok": True,
                "external_id": f"stub_task_{datetime.utcnow().timestamp()}",
                "raw": {"id": 12345, "title": payload.get("title", "")},
            }
            # Log to database
            import asyncio
            asyncio.run(self._log_call(payload, response, self.mode))
            return response
        else:
            # Live mode - make actual HTTP request
            return self._create_task_live(payload)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _create_task_live(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create task in Bitrix (live mode)."""
        if not self.base_url or not self.access_token:
            raise ValueError("Bitrix credentials not configured")

        url = f"{self.base_url}/tasks.task.add"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        with httpx.Client() as client:
            response = client.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            result = {
                "ok": True,
                "external_id": str(data.get("result", {}).get("task", {}).get("id", "")),
                "raw": data,
            }

            # Log to database
            import asyncio
            asyncio.run(self._log_call(payload, result, self.mode))
            return result

    def update_task(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update a task in Bitrix."""
        if self.mode == BitrixMode.STUB:
            response = {
                "ok": True,
                "external_id": external_id,
                "raw": {"id": external_id, "updated": True},
            }
            import asyncio
            asyncio.run(self._log_call(payload, response, self.mode))
            return response
        else:
            return self._update_task_live(external_id, payload)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _update_task_live(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update task in Bitrix (live mode)."""
        if not self.base_url or not self.access_token:
            raise ValueError("Bitrix credentials not configured")

        url = f"{self.base_url}/tasks.task.update"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload["taskId"] = external_id

        with httpx.Client() as client:
            response = client.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            result = {
                "ok": True,
                "external_id": external_id,
                "raw": data,
            }

            import asyncio
            asyncio.run(self._log_call(payload, result, self.mode))
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
        if not self.base_url or not self.access_token:
            raise ValueError("Bitrix credentials not configured")

        url = f"{self.base_url}/tasks.task.get"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"taskId": external_id}

        with httpx.Client() as client:
            response = client.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            result = {
                "ok": True,
                "external_id": external_id,
                "raw": data,
            }

            import asyncio
            asyncio.run(self._log_call({"external_id": external_id}, result, self.mode))
            return result


# Global instance
bitrix_integration = BitrixIntegration()

