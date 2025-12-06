from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Finding(BaseModel):
    id: str = Field(..., description="Уникальный ID")
    path: str = Field(..., description="Путь к файлу, где найден секрет")
    line: Optional[int] = Field(None, description="Номер строки в файле")
    key: Optional[str] = Field(None, description="Имя секрета")
    value: Optional[str] = Field(None, description="Значения секрета")
    context: Optional[str] = Field(None, description="Окружающий текст")

    extra: Dict[str, Any] = Field(default_factory=dict, description="Произвольные дополнительные поля")


class ModerateRequest(BaseModel):
    source: str = Field(..., description="Название сканера")
    findings: List[Finding]


class ModerationResult(BaseModel):
    id: str = Field(..., description="ID сработки (сквозной из Finding.id)")
    is_false_positive: bool = Field(
        ..., description="True, если по эвристикам похоже на FP"
    )
    fp_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Оценка [0;1], насколько это похоже на FP"
    )
    entropy: float = Field(
        ..., description="Энтропия значения секрета (Shannon, бит/символ)"
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="Список сработавших эвристик (для explainability)",
    )


class ModerateResponse(BaseModel):
    results: List[ModerationResult]
