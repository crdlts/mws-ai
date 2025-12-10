# llm_detector.py
import json
import os
import re
import logging
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("moderator.llm")

QWEN_URL = "https://qwen3.product.nova.neurotech.k2.cloud"
QWEN_TOKEN = os.getenv("QWEN_API_KEY")


class QwenLLM:
    def __init__(self, url: str = QWEN_URL, api_token: Optional[str] = QWEN_TOKEN):
        self.url = url
        self.token = api_token

    async def classify(
        self,
        secret: str,
        file_path: Optional[str],
        context: Optional[str],
    ) -> Dict[str, Any]:
        if not self.token:
            logger.error("QWEN_API_KEY is not set")
            # Не валим модератор целиком
            return {
                "verdict": "TP",
                "confidence": 0.5,
                "reason": "LLM token missing",
            }

        # 🔧 Исправленный промпт — без невалидного JSON-шаблона
        prompt = f"""
You are a JSON-only classifier.

Task: decide if this value is a REAL secret (TP) or a TEST placeholder (FP).

SECRET: {secret}
FILE: {file_path}
CONTEXT: {context}

Return ONLY valid JSON with the following keys:
- "verdict": string, either "TP" or "FP"
- "confidence": float between 0.0 and 1.0
- "reason": short string explanation.

Do not include any extra text, comments, or markdown. Output JSON only.
""".strip()

        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                resp = await client.post(
                    self.url,
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"inputs": prompt},
                )

            logger.info(
                "LLM response status=%s body_head=%s",
                resp.status_code,
                resp.text[:300],
            )
            resp.raise_for_status()

            # 1) Парсим общий JSON-ответ сервера
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                logger.error("Failed to decode resp.json(): %r, body=%s", e, resp.text)
                return {
                    "verdict": "TP",
                    "confidence": 0.5,
                    "reason": "LLM invalid JSON response",
                }

            # 2) Достаём generated_text
            text = ""
            if isinstance(data, list) and data and isinstance(data[0], dict):
                text = data[0].get("generated_text", "") or ""
            elif isinstance(data, dict):
                text = data.get("generated_text", "") or data.get("output_text", "") or ""
            else:
                logger.error("Unexpected LLM JSON structure: %r", data)
                return {
                    "verdict": "TP",
                    "confidence": 0.5,
                    "reason": "LLM unexpected json structure",
                }

            # 3) Ищем JSON с нужными полями, берём ПОСЛЕДНИЙ матч
            pattern = r"\{[^{}]*\"verdict\"[^{}]*\"confidence\"[^{}]*\"reason\"[^{}]*\}"
            matches = list(re.finditer(pattern, text, re.DOTALL))

            if not matches:
                logger.error(
                    "Could not find JSON block in generated_text. generated_text head: %s",
                    text[:300],
                )
                return {
                    "verdict": "TP",
                    "confidence": 0.5,
                    "reason": "LLM no json block found",
                }

            json_str = matches[-1].group(0)

            # 4) Пробуем распарсить найденный кусок как JSON
            try:
                parsed = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(
                    "JSONDecodeError on extracted json_str: %r, json_str=%s",
                    e,
                    json_str,
                )
                return {
                    "verdict": "TP",
                    "confidence": 0.5,
                    "reason": "LLM invalid json block",
                }

            # 5) нормализуем выход
            verdict = parsed.get("verdict", "TP")
            try:
                confidence = float(parsed.get("confidence", 0.5))
            except (TypeError, ValueError):
                confidence = 0.5
            reason = parsed.get("reason", "")

            return {
                "verdict": verdict,
                "confidence": confidence,
                "reason": reason,
            }

        except httpx.HTTPError as e:
            logger.error("LLM HTTP error: %r", e)
            return {
                "verdict": "TP",
                "confidence": 0.5,
                "reason": f"LLM HTTP error: {e}",
            }
