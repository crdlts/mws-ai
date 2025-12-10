from typing import List
from .schemas import Finding, ModerationResult
from .heuristics import evaluate_finding
from .ml_model import CatBoostModel
from .llm_detector import QwenLLM


class ModeratorPipeline:
    def __init__(self, catboost_model: CatBoostModel, llm: QwenLLM):
        self.catboost_model = catboost_model
        self.llm = llm

    async def process_findings(self, findings: List[Finding]) -> List[ModerationResult]:
        results: List[ModerationResult] = []

        for f in findings:
            heur = evaluate_finding(f)

            # Если эвристика уверена, что это FP — сразу возвращаем
            if heur.is_false_positive:
                results.append(
                    ModerationResult(
                        id=f.id,
                        is_false_positive=True,
                        fp_score=1.0,
                        entropy=heur.entropy,
                        reasons=heur.reasons,
                    )
                )
                continue

            # ---- ФИЧИ ДЛЯ CATBOOST (как в трейне) ----

            path = f.path or ""
            key = f.key or "unknown_rule"
            value = f.value or ""
            context = f.context or ""

            # ruleId берём из key
            rule_id = key

            # длина значения секрета
            length = len(value)

            # энтропия уже посчитана эвристикой
            entropy = heur.entropy

            # признак "есть fp-ключевые слова" в контексте/значении
            fp_keywords = ["todo", "fixme", "dummy", "example", "sample", "test", "fake"]
            text_for_fp = f"{context} {value}".lower()
            has_fp_keyword = int(any(kw in text_for_fp for kw in fp_keywords))

            # признак "секрет в тестовом/моковом пути"
            test_markers = ["test", "tests", "/__tests__", "fixtures", "mock"]
            in_test_path = int(any(m in path.lower() for m in test_markers))

            # snippet = context + value (как ты сказал)
            snippet = f"{context} {value}".strip()

            features = {
                "ruleId": rule_id,
                "length": length,
                "entropy": entropy,
                "has_fp_keyword": has_fp_keyword,
                "in_test_path": in_test_path,
                "snippet": snippet,
            }

            # ---- вызов ML-модели ----

            ml_res = self.catboost_model.predict_one(features)
            ml_prob = ml_res.get("prob", 0.5)

            heur.fp_score = ml_prob
            heur.reasons.append(f"ml_prob={ml_prob:.3f}")
            heur.is_false_positive = ml_prob >= 0.5

            # зона неопределённости — подключаем LLM
            if 0.35 < ml_prob < 0.65:
                llm_res = await self.llm.classify(
                    secret=f.value,
                    file_path=f.path,
                    context=f.context,
                )
                verdict = llm_res.get("verdict", "TP")
                llm_conf = float(llm_res.get("confidence", 0.5))

                heur.fp_score = (ml_prob + llm_conf) / 2
                heur.is_false_positive = verdict == "FP"
                heur.reasons.append(f"llm={verdict},conf={llm_conf:.2f}")

            results.append(
                ModerationResult(
                    id=f.id,
                    is_false_positive=heur.is_false_positive,
                    fp_score=heur.fp_score,
                    entropy=heur.entropy,
                    reasons=heur.reasons,
                )
            )

        return results
