import uuid
import logging
from typing import Optional

from fastapi import FastAPI, Request

from .schemas import ModerateResponse, ModerateRequest
from .heuristics import evaluate_finding
from common.audit_client import AuditClient  # 👈 общий клиент

# Базовый логгер (stdout контейнера)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("moderator")

# Общий audit-клиент для сервиса модерации
audit = AuditClient(service_name="moderator")


app = FastAPI(
    title="Moderator Service",
    description="Модератор на эвристиках",
    version="0.1.0",
)


# ---- Middleware для trace_id ----

@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """
    Прокидываем/генерируем X-Trace-Id:
    - если пришёл от оркестратора — используем его,
    - иначе генерируем новый.
    """
    incoming_trace_id = request.headers.get("X-Trace-Id")
    trace_id = incoming_trace_id or str(uuid.uuid4())

    request.state.trace_id = trace_id

    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


# ---- Эндпоинты ----

@app.get("/health")
async def health(request: Request):
    trace_id: Optional[str] = getattr(request.state, "trace_id", None)

    await audit.log(
        level="INFO",
        message="Moderator health check",
        trace_id=trace_id,
        context={"path": str(request.url.path)},
    )

    return {"status": "OK"}


@app.post("/moderate", response_model=ModerateResponse)
async def moderate(req: ModerateRequest, request: Request) -> ModerateResponse:
    trace_id: Optional[str] = getattr(request.state, "trace_id", None)
    # report_id можно прокидывать в теле запроса при желании
    report_id = getattr(req, "report_id", None) if hasattr(req, "report_id") else None

    logger.info(
        "Moderator received request: num_findings=%d trace_id=%s report_id=%s",
        len(req.findings),
        trace_id,
        report_id,
    )

    await audit.log(
        level="INFO",
        message="Moderator received findings batch",
        trace_id=trace_id,
        report_id=report_id,
        context={
            "num_findings": len(req.findings),
            # важно: не логируем сами secret_snippet, чтобы не сливать секреты в аудит
        },
    )

    # Основная логика модерации
    results = [evaluate_finding(f) for f in req.findings]

    # Немного агрегированной статистики для аудита
    suspicious_count = 0
    for r in results:
        # предполагаем, что в результате может быть поле is_false_positive
        is_fp = getattr(r, "is_false_positive", None)
        if is_fp is False:
            suspicious_count += 1

    await audit.log(
        level="INFO",
        message="Moderator processed findings",
        trace_id=trace_id,
        report_id=report_id,
        context={
            "num_findings": len(results),
            "num_suspicious": suspicious_count,
        },
    )

    return ModerateResponse(results=results)
