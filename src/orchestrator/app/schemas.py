# app/schemas.py
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    tool: str = Field(..., description="Имя инструмента: gitleaks, trivy, gitguardian и т.п.")
    report: Dict[str, Any] = Field(
        ...,
        description="Исходный отчёт сканера (SARIF или другой JSON).",
    )


class AnalyzeResponse(BaseModel):
    report_id: str
    status: Literal["pending", "in_progress", "completed", "failed"]


class Finding(BaseModel):
    rule_id: str = Field(..., description="ID правила из сканера (например, aws-access-key).")
    file_path: str = Field(..., description="Путь к файлу в репозитории.")
    secret_snippet: str = Field(..., description="Фрагмент потенциального секрета.")
    is_false_positive: bool = Field(
        ...,
        description="Решение системы: является ли находка ложноположительной.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Уверенность модели/системы (0..1).",
    )
    ai_verdict: Optional[str] = Field(
        default=None,
        description="Текстовое объяснение от AI/эвристик.",
    )
    # В примере: "original_location": { ... }
    original_location: Dict[str, Any] = Field(
        ...,
        description="Сырые данные о местоположении секрета (кусок SARIF/JSON).",
    )


class Stats(BaseModel):
    total_findings: int = Field(..., description="Всего находок в исходном отчёте.")
    filtered_fp: int = Field(..., description="Сколько отфильтровано как false positive.")
    remaining_tp: int = Field(..., description="Сколько осталось потенциальных true positive.")


class TaskStatusResponse(BaseModel):
    report_id: str
    status: Literal["pending", "in_progress", "completed", "failed"]

    # Пока делаем опциональными — на статусах pending/failed могут быть пустые.
    findings: Optional[List[Finding]] = None
    stats: Optional[Stats] = None
    error: Optional[str] = None
