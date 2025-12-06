from typing import Any, Dict
import httpx
from .config import settings


class ModeratorClient:
    """
    Клиент для общения с сервисом Moderator.
    POST /analyze.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.MODERATOR_URL

    async def analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/moderate"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()


class ReportInjestorClient:
    """
    Клиент для общения с сервисом report_injestor.
    POST /api/normalize.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.REPORT_INJESTOR_URL

    async def normalize(self, raw_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        raw_report — это тот самый SARIF/JSON, который лежит в task.request_payload.
        """
        url = f"{self.base_url}/api/normalize"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=raw_report)
            resp.raise_for_status()
            return resp.json()


moderator_client = ModeratorClient()
report_injestor_client = ReportInjestorClient()