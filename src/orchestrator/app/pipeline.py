from typing import Any, Dict, List

from .models import Task
from .storage import storage
from .clients import moderator_client, report_injestor_client


async def run_pipeline_for_task(task: Task) -> None:
    task.set_status("in_progress")
    storage.update(task)

    try:
        # 1) Берём сырой отчёт от сканера (SARIF/JSON), который прилетел в /api/analyze
        raw_report: Dict[str, Any] = task.request_payload or {}

        # 2) Отдаём сырой отчёт в report_injestor, чтобы он его нормализовал
        normalized = await report_injestor_client.normalize(raw_report)

        # 3) Преобразуем нормализованные фичи в формат, который ожидает модератор
        normalized_findings: List[Dict[str, Any]] = normalized.get("findings", [])
        moderator_findings: List[Dict[str, Any]] = []

        for idx, f in enumerate(normalized_findings):
            finding_id = str(idx)
            meta = f.get("metadata") or {}

            moderator_findings.append(
                {
                    "id": finding_id,
                    "path": f.get("file_path"),
                    "line": f.get("line"),
                    "key": None,  # пока не из чего брать
                    "value": f.get("message"),
                    # БЕРЁМ snippet ИЗ metadata вместо пустой строки
                    "context": meta.get("snippet") or "",
                    "extra": {
                        "rule_id": f.get("rule_id"),
                        "scanner": f.get("scanner"),
                        "severity": f.get("severity"),
                        "rule_name": meta.get("rule_name"),
                    },
                }
            )

        # 4) Вызываем модератор
        moderator_payload: Dict[str, Any] = {
            # если report_injestor вернул source — можем использовать его;
            # иначе оставим старый task.source (например 'gitleaks', 'semgrep' и т.п.)
            "source": normalized.get("source") or task.source,
            "findings": moderator_findings,
        }

        moderation = await moderator_client.analyze(moderator_payload)

        # 5) Собираем ответ для API
        results = moderation.get("results", [])
        mod_by_id = {r["id"]: r for r in results}

        api_findings: List[Dict[str, Any]] = []
        for f in moderator_findings:
            mod = mod_by_id.get(f["id"], {})

            fp_score = float(mod.get("fp_score", 0.0))
            reasons = mod.get("reasons", []) or []

            api_findings.append(
                {
                    "rule_id": f["extra"]["rule_id"],
                    "file_path": f["path"],
                    "secret_snippet": f["context"] or f["value"],
                    "is_false_positive": bool(mod.get("is_false_positive", False)),
                    # «насколько уверен, что это TP»
                    "confidence": float(1.0 - fp_score),
                    "fp_score": fp_score,
                    "reasons": reasons,
                    "ai_verdict": None,  # на будущее под LLM
                    "original_location": {
                        "path": f["path"],
                        "line": f["line"],
                    },
                }
            )

        # 6) Сохраняем результат
        task.result = {
            "findings": api_findings,
            "stats": None,   # здесь потом можно посчитать агрегаты
        }
        task.set_status("completed")
        storage.update(task)

    except Exception as exc:  # noqa: BLE001
        task.error = str(exc)
        task.set_status("failed")
        storage.update(task)
