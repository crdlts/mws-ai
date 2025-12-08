import httpx
import json
import os

QWEN_URL = "https://qwen3.product.nova.neurotech.k2.cloud"
QWEN_TOKEN = os.getenv("QWEN_API_KEY")  

class QwenLLM:
    def __init__(self, url=QWEN_URL, api_token=QWEN_TOKEN):
        self.url = url
        self.token = api_token

    async def classify(self, secret: str, file_path: str, context: str):
        prompt = f"""
Classify: is this value a REAL secret (TP) or TEST placeholder (FP)?

SECRET: {secret}
FILE: {file_path}
CONTEXT: {context}

Return strictly JSON:
{{
  "verdict": "TP" or "FP",
  "confidence": 0.0-1.0,
  "reason": "text"
}}
"""
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.post(
                self.url,
                headers={"Authorization": f"Bearer {self.token}"},
                json={"inputs": prompt}
            )
        text = r.json()[0]["generated_text"]
        return json.loads(text)
