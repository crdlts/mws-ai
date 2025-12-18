import os
from typing import List
from .schemas import Finding, ModerationResult
from .heuristics import evaluate_finding
from .onnx_model import CharCNNOnnxModel as CharCNNModel
from .llm_detector import QwenLLM

CNN_THRESHOLD = float(os.getenv("CNN_THRESHOLD", "0.45"))        # порог по FP score
UNCERT_LOW = float(os.getenv("CNN_UNCERT_LOW", "0.30"))
UNCERT_HIGH = float(os.getenv("CNN_UNCERT_HIGH", "0.70"))


class ModeratorPipeline:
    def __init__(self, cnn_model: CharCNNModel, llm: QwenLLM):
        self.cnn_model = cnn_model
        self.llm = llm

    async def process_findings(self, findings: List[Finding]) -> List[ModerationResult]:
        results: List[ModerationResult] = []

        for f in findings:
            heur = evaluate_finding(f)

            # 1) если эвристика уже уверена, что FP — как и раньше
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

            # 2) CNN работает ТОЛЬКО по candidate=value (как в обучении)
            value = f.value or ""
            prob_tp = self.cnn_model.predict_prob_tp(value)
            fp_score = 1.0 - prob_tp

            heur.fp_score = fp_score
            heur.reasons.append(f"cnn_prob_tp={prob_tp:.3f}")
            heur.reasons.append(f"cnn_fp_score={fp_score:.3f}")

            heur.is_false_positive = fp_score >= CNN_THRESHOLD

            # 3) зона неопределенности -> LLM (лучше оставлять)
            if UNCERT_LOW < fp_score < UNCERT_HIGH:
                llm_res = await self.llm.classify(
                    secret=f.value,
                    file_path=f.path,
                    context=f.context,
                )
                verdict = llm_res.get("verdict", "TP")
                llm_conf = float(llm_res.get("confidence", 0.5))

                # аккуратное объединение:
                # prob_tp_final = avg(prob_tp, llm_prob_tp)
                llm_prob_tp = llm_conf if verdict == "TP" else (1.0 - llm_conf)
                prob_tp_final = 0.5 * prob_tp + 0.5 * llm_prob_tp
                fp_score = 1.0 - prob_tp_final

                heur.fp_score = fp_score
                heur.is_false_positive = fp_score >= CNN_THRESHOLD
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
