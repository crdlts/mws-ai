from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import pathlib
import asyncio

LOGS_DIR = pathlib.Path("./logs")  # локальная папка рядом с main.py
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "audit.jsonl"

app = FastAPI(title="Audit service")
_write_lock = asyncio.Lock()


class LogEvent(BaseModel):
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    service: str
    level: str = "INFO"
    message: str
    trace_id: Optional[str] = None
    report_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


async def append_log(event: LogEvent) -> None:
    # ✅ pydantic сам превращает datetime → строку
    try:
        # Pydantic v2
        line = event.model_dump_json()
    except AttributeError:
        # Pydantic v1 (на всякий случай)
        line = event.json()

    async with _write_lock:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


@app.get("/health")  # 👈 Добавить health endpoint
async def health():
    return {"status": "ok", "service": "audit"}


@app.post("/audit/log")
async def write_log(event: LogEvent):
    try:
        await append_log(event)
    except Exception as e:
        # на время отладки можно явно вернуть ошибку
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}