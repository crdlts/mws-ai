# report_injestor/app/main.py
import logging
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request

from .api import router as api_router
from .config import settings
from common.audit_client import AuditClient  # 👈 общий клиент


# --- базовый логгер (stdout контейнера) ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("report_ingestor")

# --- общий audit-клиент для этого сервиса ---

audit = AuditClient(service_name=settings.PROJECT_NAME or "report_ingestor")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
    )

    # --- middleware: trace_id + audit http-запросов ---
    @app.middleware("http")
    async def trace_and_audit_middleware(request: Request, call_next):
        """
        - Прокидывает/генерирует X-Trace-Id
        - Логирует запрос/ответ в audit-сервис
        """
        # trace_id: берём из заголовка или генерируем
        incoming_trace_id = request.headers.get("X-Trace-Id")
        trace_id = incoming_trace_id or str(uuid.uuid4())

        request.state.trace_id = trace_id

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000.0

        response.headers["X-Trace-Id"] = trace_id

        # Пытаемся выдернуть report_id из path_params (если есть)
        report_id: Optional[str] = None
        if "report_id" in request.path_params:
            report_id = str(request.path_params["report_id"])

        # Отправляем событие в audit
        await audit.log(
            level="INFO",
            message="HTTP request handled by report_ingestor",
            trace_id=trace_id,
            report_id=report_id,
            context={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response

    @app.get("/health")  # 👈 Добавить health endpoint
    async def health():
        return {"status": "ok", "service": "report_ingestor"}

    app.include_router(api_router)
    return app


app = create_app()
