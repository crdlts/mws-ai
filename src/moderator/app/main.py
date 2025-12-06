from fastapi import FastAPI

from .schemas import ModerateResponse, ModerateRequest
from .heuristics import evaluate_finding


app = FastAPI(
    title="Moderator Service",
    description="Модератор на эвристиках",
    version="0.1.0"
)


@app.get("/health")
async def health():
    return {"status": "OK"}


@app.post("/moderate", response_model=ModerateResponse)
async def moderate(req: ModerateRequest) -> ModerateResponse:
    results = [evaluate_finding(f) for f in req.findings]
    return ModerateResponse(results=results)
