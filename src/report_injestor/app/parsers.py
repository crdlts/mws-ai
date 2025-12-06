# report_injestor/app/parsers.py
from typing import Any, Dict, List

from .schemas import NormalizedFinding, NormalizeResponse


def detect_scanner(raw: Dict[str, Any]) -> str:
    """
    Определяем тип входного отчёта.

    Сейчас у нас два варианта:
    - SARIF (есть ключ 'runs')
    - generic / semgrep-подобные форматы (на будущее)
    """
    # SARIF-отчёты всегда содержат ключ "runs" на верхнем уровне
    if "runs" in raw:
        return "sarif"

    tool = (raw.get("tool") or raw.get("scanner") or "").lower()
    if "semgrep" in tool:
        return "semgrep"

    return "generic"


def parse_sarif(raw: Dict[str, Any]) -> NormalizeResponse:
    """
    Парсим SARIF (то, что раньше ты делал в оркестраторе в pipeline.py).

    Ожидаем что-то вроде:
    {
      "runs": [
        {
          "tool": { "driver": { "rules": [ ... ] } },
          "results": [ ... ]
        }
      ]
    }
    """
    runs: List[Dict[str, Any]] = raw.get("runs", [])
    findings: List[NormalizedFinding] = []

    for run_idx, run in enumerate(runs):
        driver = (run.get("tool") or {}).get("driver") or {}
        rules = {r["id"]: r for r in driver.get("rules", [])}

        for res_idx, res in enumerate(run.get("results", [])):
            rule_id = res.get("ruleId")
            rule = rules.get(rule_id, {})

            message = (res.get("message") or {}).get("text")

            locations = res.get("locations") or []
            loc0 = locations[0] if locations else {}
            physical = loc0.get("physicalLocation", {})
            artifact = physical.get("artifactLocation", {})
            region = physical.get("region", {})

            file_path = artifact.get("uri", "")
            line = region.get("startLine")
            snippet = (region.get("snippet") or {}).get("text")

            # уровень важности — из result.level или из правила
            level = (
                res.get("level")
                or (rule.get("defaultConfiguration") or {}).get("level")
                or "unknown"
            )

            findings.append(
                NormalizedFinding(
                    scanner="sarif",
                    rule_id=rule_id or "UNKNOWN_RULE",
                    severity=str(level).lower(),
                    message=message or snippet or "",
                    file_path=file_path,
                    line=line,
                    metadata={
                        "rule_name": rule.get("name"),
                        "snippet": snippet,
                        "run_index": run_idx,
                        "result_index": res_idx,
                        "raw_result": res,
                    },
                )
            )

    return NormalizeResponse(
        source=raw.get("source"),  # при желании можно сюда класть repo/commit
        findings=findings,
        metadata={
            "format": "sarif",
            "sarif_version": raw.get("version"),
        },
    )


def parse_semgrep(raw: Dict[str, Any]) -> NormalizeResponse:
    """
    На будущее — пример для semgrep-подобного формата.
    Сейчас, если ты работаешь только с SARIF, это можно не использовать.
    """
    results = raw.get("results", [])
    findings: List[NormalizedFinding] = []

    for r in results:
        loc = r.get("location", {})
        extra = r.get("extra", {})

        findings.append(
            NormalizedFinding(
                scanner="semgrep",
                rule_id=r.get("rule", "UNKNOWN_RULE"),
                severity=str(r.get("severity_level", "unknown")).lower(),
                message=r.get("message", ""),
                file_path=loc.get("file", ""),
                line=loc.get("line"),
                metadata={
                    "raw": r,
                    "commit": extra.get("commit"),
                    "repo": extra.get("repo"),
                },
            )
        )

    return NormalizeResponse(
        source=raw.get("repo") or raw.get("source"),
        findings=findings,
        metadata={
            "scanner": "semgrep",
            "tool": raw.get("tool"),
        },
    )


def parse_generic(raw: Dict[str, Any]) -> NormalizeResponse:
    """
    Запасной вариант, если формат уже близок к нормализованному.
    Ожидаем:
    {
      "source": "...",
      "scanner": "my_scanner",
      "results": [
        {
          "rule_id": "...",
          "severity": "high",
          "message": "...",
          "file_path": "src/a.py",
          "line": 10
        }
      ]
    }
    """
    scanner = raw.get("scanner", "generic")
    results = raw.get("results", [])
    findings: List[NormalizedFinding] = []

    for r in results:
        findings.append(
            NormalizedFinding(
                scanner=scanner,
                rule_id=r.get("rule_id", "UNKNOWN_RULE"),
                severity=str(r.get("severity", "unknown")).lower(),
                message=r.get("message", ""),
                file_path=r.get("file_path", ""),
                line=r.get("line"),
                metadata={
                    k: v
                    for k, v in r.items()
                    if k not in {"rule_id", "severity", "message", "file_path", "line"}
                },
            )
        )

    return NormalizeResponse(
        source=raw.get("source"),
        findings=findings,
        metadata={"scanner": scanner},
    )


def normalize_report(raw: Dict[str, Any]) -> NormalizeResponse:
    """
    Главная точка входа: выбираем нужный парсер и возвращаем NormalizeResponse.
    """
    scanner = detect_scanner(raw)

    if scanner == "sarif":
        return parse_sarif(raw)

    if scanner == "semgrep":
        return parse_semgrep(raw)

    return parse_generic(raw)
