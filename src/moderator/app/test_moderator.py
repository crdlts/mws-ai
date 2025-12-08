import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from moderator.app.schemas import Finding
from moderator.app.pipeline import ModeratorPipeline

sample_findings = [
    Finding(
        id="f1",
        path="tests/example.json",
        key="dummy_key",
        value="value123",
        context="some comment"
    ),
    Finding(
        id="f2",
        path="src/secret/prod.json",
        key="SECRET_TOKEN",
        value="SUPERSECRET",
        context="production"
    ),
    Finding(
        id="f3",
        path="examples/config.yaml",
        key="placeholder",
        value="12345",
        context="todo fixme"
    ),
]


@pytest.mark.asyncio
async def test_moderator_pipeline():
    catboost_mock = Mock()
    catboost_mock.predict_one.side_effect = [
        {"pred": True, "prob": 0.9},   # FP
        {"pred": False, "prob": 0.2},  # TP
        {"pred": True, "prob": 0.8},   # FP
    ]

    # LLM асинхронный мок
    llm_mock = AsyncMock()
    llm_mock.classify.side_effect = [
        {"verdict": "FP", "confidence": 0.7, "reason": "looks fake"},
        {"verdict": "TP", "confidence": 0.95, "reason": "looks real"},
        {"verdict": "FP", "confidence": 0.6, "reason": "example placeholder"},
    ]

    pipeline = ModeratorPipeline(catboost_mock, llm_mock)
    results = await pipeline.process_findings(sample_findings)


    print("\n===== Moderation Results =====")
    for r in results:
        print(f"ID: {r.id}")
        print(f"  FP: {r.is_false_positive}")
        print(f"  Score: {r.fp_score:.2f}")
        print(f"  Entropy: {r.entropy:.2f}")
        print(f"  Reasons: {', '.join(r.reasons)}\n")

    assert len(results) == len(sample_findings)


if __name__ == "__main__":
    asyncio.run(test_moderator_pipeline())
