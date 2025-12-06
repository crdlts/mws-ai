# src/report_injector/app/api.py
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from .schemas import NormalizeResponse
from .parsers import normalize_report

router = APIRouter(prefix="/api", tags=["report-injector"])


@router.post("/normalize", response_model=NormalizeResponse)
async def normalize_endpoint(raw_report: Dict[str, Any]) -> NormalizeResponse:
    """
    Принимает сырой JSON от оркестратора, возвращает нормализованный отчет.
    Оркестратор уже дальше решает, как это прокинуть в модератор.
    """
    try:
        return normalize_report(raw_report)
    except Exception as exc:
        # тут можно логировать ошибку подробнее
        raise HTTPException(status_code=400, detail=f"Failed to normalize report: {exc}")
