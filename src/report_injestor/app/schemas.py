# src/report_injector/app/schemas.py
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NormalizedFinding(BaseModel):
    """
    Единый формат одной находки, который дальше пойдёт в оркестратор/модератор.
    """
    scanner: str = Field(..., description="Имя сканера, например 'semgrep'")
    rule_id: str = Field(..., description="Идентификатор правила/правила сканера")
    severity: str = Field(..., description="Уровень важности: low/medium/high/critical")
    message: str = Field(..., description="Текст описания проблемы")
    file_path: str = Field(..., description="Путь до файла в репозитории")
    line: Optional[int] = Field(None, description="Номер строки, если есть")

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Доп. инфа по находке (commit, rule_name и т.п.)",
    )


class NormalizeResponse(BaseModel):
    """
    То, что Report Injector вернёт в оркестратор.
    """
    source: Optional[str] = Field(
        None,
        description="Источник отчета: репозиторий, pipeline id и т.п.",
    )
    findings: List[NormalizedFinding]
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Метаданные отчёта: имя сканера, версия, commit и т.п.",
    )
