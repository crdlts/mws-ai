# pipeline_init.py
import os
import logging
from .ml_model import CatBoostModel
from .llm_detector import QwenLLM
from .pipeline import ModeratorPipeline

logger = logging.getLogger("moderator.init")

BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.getenv("CATBOOST_MODEL_PATH", os.path.join(BASE_DIR, "catboost_model.cbm"))

catboost_model = CatBoostModel(MODEL_PATH)
llm = QwenLLM(api_token=os.getenv("QWEN_API_KEY"))

moderator_pipeline = ModeratorPipeline(catboost_model=catboost_model, llm=llm)

async def moderate_finding(findings):
    return await moderator_pipeline.process_findings(findings)
