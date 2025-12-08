import uuid
import logging
from typing import Optional
from fastapi import FastAPI, Request
from .schemas import ModerateResponse, ModerateRequest, ModerationResult
from common.audit_client import AuditClient
from .pipeline_init import moderate_finding

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("moderator")

audit = AuditClient(service_name="moderator")

app = FastAPI(
    title="Moderator Service",
    description="Модератор на эвристиках + ML + LLM",
    version="0.1.0",
)

@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    incoming_trace_id = request.headers.get("X-Trace-Id")
    trace_id = incoming_trace_id or str(uuid.uuid4())
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response

@app.get("/health")
async def health(request: Request):
    trace_id: Optional[str] = getattr(request.state, "trace_id", None)
    await audit.log(level="INFO", message="Moderator health check", trace_id=trace_id,
                    context={"path": str(request.url.path)})
    return {"status": "OK"}

@app.post("/moderate", response_model=ModerateResponse)
async def moderate(req: ModerateRequest, request: Request) -> ModerateResponse:
    trace_id: Optional[str] = getattr(request.state, "trace_id", None)
    report_id = getattr(req, "report_id", None) if hasattr(req, "report_id") else None

    logger.info("Moderator received request: num_findings=%d trace_id=%s report_id=%s",
                len(req.findings), trace_id, report_id)

    raw_results = await moderate_finding(req.findings)

    results = [
        ModerationResult(
            id=r.id,
            is_false_positive=r.is_false_positive,
            fp_score=r.fp_score,
            entropy=r.entropy,
            reasons=r.reasons,
        )
        for r in raw_results
    ]

    suspicious_count = sum(1 for r in results if r.is_false_positive is False)

    await audit.log(level="INFO", message="Moderator processed findings",
                    trace_id=trace_id, report_id=report_id,
                    context={"num_findings": len(results), "num_suspicious": suspicious_count})

    return ModerateResponse(results=results)
