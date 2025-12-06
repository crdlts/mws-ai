import uuid

from fastapi import FastAPI, BackgroundTasks, HTTPException

from .config import settings
from .schemas import AnalyzeRequest, AnalyzeResponse, TaskStatusResponse
from .models import Task
from .storage import storage
from .pipeline import run_pipeline_for_task


app = FastAPI(title=settings.PROJECT_NAME)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    report_id = str(uuid.uuid4())

    task = Task(
        id=report_id,
        status="pending",
        source=request.tool,
        metadata=None,            # при необходимости
        request_payload=request.report,
    )

    storage.save(task)

    # Запускаем пайплайн в фоне
    background_tasks.add_task(run_pipeline_for_task, task)

    return AnalyzeResponse(report_id=report_id, status=task.status)


@app.get("/api/reports/{report_id}", response_model=TaskStatusResponse)
async def get_report(report_id: str):
    task = storage.get(report_id)
    if not task:
        raise HTTPException(status_code=404, detail="Report not found")

    findings = None
    stats = None

    if isinstance(task.result, dict):
        findings = task.result.get("findings")
        stats = task.result.get("stats")

    return TaskStatusResponse(
        report_id=task.id,
        status=task.status,
        findings=findings,
        stats=stats,
        error=task.error
    )
