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
            
            features = {
                "entropy": heur.entropy,
                "path_length": len(f.path or ""),
                "key_length": len(f.key or ""),
                "value_length": len(f.value or ""),
                "comment_marker": int(any(c in (f.context or "").lower() for c in ["todo", "fixme"]))
            }

            ml_res = self.catboost_model.predict_one(features)
            ml_prob = ml_res.get("prob", 0.5)
            heur.fp_score = ml_prob
            heur.reasons.append(f"ml_prob={ml_prob:.3f}")
            heur.is_false_positive = ml_prob >= 0.5

            if 0.35 < ml_prob < 0.65:
                llm_res = await self.llm.classify(
                        secret=f.value,
                        file_path=f.path,
                        context=f.context
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
                    reasons=heur.reasons
                )
            )

        return results
