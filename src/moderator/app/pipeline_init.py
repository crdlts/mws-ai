import os
import logging
#from .cnn_model import CharCNNModel
from .onnx_model import CharCNNOnnxModel
from .llm_detector import QwenLLM
from .pipeline import ModeratorPipeline

logger = logging.getLogger("moderator.init")

BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.getenv("CNN_MODEL_DIR", os.path.join(BASE_DIR, "models"))
MAX_LEN = int(os.getenv("CNN_MAX_LEN", "256"))
DEVICE = os.getenv("CNN_DEVICE", "cpu")

#cnn_model = CharCNNModel(model_dir=MODEL_DIR, max_len=MAX_LEN, device=DEVICE)
cnn_model = CharCNNOnnxModel(model_dir=MODEL_DIR, max_len=MAX_LEN)
llm = QwenLLM(api_token=os.getenv("QWEN_API_KEY"))

moderator_pipeline = ModeratorPipeline(cnn_model=cnn_model, llm=llm)

async def moderate_finding(findings):
    return await moderator_pipeline.process_findings(findings)
