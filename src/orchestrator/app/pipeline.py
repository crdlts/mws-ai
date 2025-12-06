# orchestrator/app/pipeline.py

import logging
from typing import Any, Dict, List

from .models import Task
from .storage import storage
from .clients import moderator_client

logger = logging.getLogger(__name__)


async def run_pipeline_for_task(task: Task) -> None:
    logger.info("Start pipeline for task %s", task.id)
    task.set_status("in_progress")
    storage.update(task)

    try:
        # 1) Берём SARIF-отчёт от сканера (то, что пришло в request.report)
        sarif: Dict[str, Any] = task.request_payload or {}
        runs: List[Dict[str, Any]] = sarif.get("runs", [])

        # ---------- НОРМАЛИЗАЦИЯ ДЛЯ МОДЕРАТОРА ----------
        moderator_findings: List[Dict[str, Any]] = []

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

                file_path = artifact.get("uri")
                line = region.get("startLine")
                snippet = (region.get("snippet") or {}).get("text")

                finding_id = f"{run_idx}:{res_idx}"

                moderator_findings.append(
                    {
                        "id": finding_id,
                        "path": file_path,
                        "line": line,
                        "key": None,
                        "value": message,
                        "context": snippet,
                        "extra": {
                            "rule_id": rule_id,
                            "rule_name": rule.get("name"),
                        },
                    }
                )

        logger.info("Normalized %d findings for moderator", len(moderator_findings))

        # ---------- ВЫЗОВ МОДЕРАТОРА ----------
        moderator_payload: Dict[str, Any] = {
            "source": task.source,          # "gitleaks"
            "findings": moderator_findings,
        }

        logger.info("Calling moderator with payload=%s", moderator_payload)
        moderation = await moderator_client.analyze(moderator_payload)
        logger.info("Moderator response: %s", moderation)

        # ---------- СБОРКА ФОРМАТА ДЛЯ ОТВЕТА API ----------
        results = moderation.get("results", [])
        mod_by_id = {r["id"]: r for r in results}

        api_findings: List[Dict[str, Any]] = []
        for f in moderator_findings:
            mod = mod_by_id.get(f["id"], {})
            api_findings.append(
                {
                    "rule_id": f["extra"]["rule_id"],
                    "file_path": f["path"],
                    "secret_snippet": f["context"] or f["value"],
                    "is_false_positive": bool(mod.get("is_false_positive", False)),
                    # можно интерпретировать как «насколько уверен, что это TP»
                    "confidence": float(1.0 - mod.get("fp_score", 0.0)),
                    "original_location": {
                        "path": f["path"],
                        "line": f["line"],
                    },
                }
            )

        # ---------- СОХРАНЯЕМ РЕЗУЛЬТАТ ЗАДАЧИ ----------
        task.result = {
            "findings": api_findings,
            "stats": None,   # тут потом можно посчитать агрегаты
        }
        task.set_status("completed")
        storage.update(task)
        logger.info("Pipeline for task %s completed", task.id)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed for task %s", task.id)
        task.error = str(exc)
        task.set_status("failed")
        storage.update(task)
