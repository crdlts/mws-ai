import math
from collections import Counter
from typing import List

from .schemas import Finding, ModerationResult


TEST_PATH_MARKERS = [
    "/test/",
    "/tests/",
    "/mock/",
    "/mocks/",
    "/example/",
    "/examples/"
]

FAKE_KEYWAORD = [
    "example",
    "fake",
    "test_key",
    "dummy",
    "sample",
    "placeholder"
]

COMMENT_MARKERS = ["todo", "fixme"]


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    count = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in count.values())


def evaluate_finding(f: Finding) -> ModerationResult:
    score = 0.0
    reasons: List[str] = []

    path = (f.path or "").lower()
    if any(marker in path for marker in TEST_PATH_MARKERS):
        score += 0.4
        reasons.append("path_looks_like_test_or_example")

    key = (f.key or "").lower()
    if any(k in key for k in FAKE_KEYWAORD):
        score += 0.4
        reasons.append("key_looks_fake_or_example")
    
    value = f.value or ""
    ent = shannon_entropy(value)
    if value and ent < 3.0: # Порог нужно еще подбирать
        score += 0.3
        reasons.append(f"low_entropy_{ent:.2f}")
    
    ctx = (f.context or "").lower()
    if any(marker in ctx for marker in COMMENT_MARKERS):
        score += 0.2
        reasons.append("inside_todo_or_fixme_comment")

    if score > 1.0:
        score = 1.0

    is_fp = score >= 0.5 # Тоже нужно подбирать

    return ModerationResult(
        id=f.id,
        is_false_positive=is_fp,
        fp_score=score,
        entropy=ent,
        reasons=reasons
    )
