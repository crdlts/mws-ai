# common/audit_client.py
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx


class AuditClient:
    """
    Лёгкий клиент для отправки логов в audit-сервис.
    Ошибки при отправке глушатся — не должны ломать основной сервис.
    """

    def __init__(
        self,
        service_name: str,
        base_url: Optional[str] = None,
        timeout: float = 1.0,
    ) -> None:
        self.service_name = service_name
        self.base_url = base_url or os.getenv("AUDIT_URL", "http://localhost:8003")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def log(
        self,
        level: str,
        message: str,
        *,
        trace_id: Optional[str] = None,
        report_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "level": level.upper(),
            "message": message,
            "trace_id": trace_id,
            "report_id": report_id,
            "context": context or {},
        }

        try:
            client = await self._get_client()
            await client.post("/audit/log", json=payload)
        except Exception:
            # Здесь без логгера специально — чтобы библиотека не писала сама в stdout
            # Если хочешь логировать ошибку, делай это снаружи.
            pass
