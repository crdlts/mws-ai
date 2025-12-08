import os
import pandas as pd
import catboost
import logging

logger = logging.getLogger("moderator.ml_model")

class CatBoostModel:
    def __init__(self, model_path: str = None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), "catboost_model.cbm")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"CatBoost model not found at {model_path}")

        self.model = catboost.CatBoostClassifier()
        try:
            self.model.load_model(model_path)
            logger.info("CatBoost model loaded successfully from %s", model_path)
        except Exception as e:
            logger.exception("Failed to load CatBoost model: %s", e)
            raise

    def predict_one(self, features: dict) -> dict:
        """
        Прогноз для одного набора признаков.
        Возвращает словарь: {"pred": bool, "prob": float}
        """
        try:
            df = pd.DataFrame([features])
            pred = int(self.model.predict(df)[0])
            prob = float(self.model.predict_proba(df)[0][1])
            return {"pred": bool(pred), "prob": prob}
        except Exception as e:
            logger.exception("CatBoost prediction failed: %s", e)
            return {"pred": False, "prob": 0.5, "error": str(e)}
