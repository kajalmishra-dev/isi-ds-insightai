import logging
import os

import joblib
import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join("ml", "artifacts", "model.joblib")


class ModelEngine:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise RuntimeError(
                f"Model not found at {MODEL_PATH}. Run: python -m ml.train"
            )

        logger.info("Loading model from %s", MODEL_PATH)
        self.model = joblib.load(MODEL_PATH)

    def predict(self, text: str):
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        probs = self.model.predict_proba([text])[0]
        classes = self.model.classes_
        max_idx = int(np.argmax(probs))

        return {
            "category": classes[max_idx],
            "confidence": float(probs[max_idx]),
        }


_engine = None


def get_engine() -> ModelEngine:
    global _engine
    if _engine is None:
        _engine = ModelEngine()
    return _engine


def predict(text: str):
    try:
        return get_engine().predict(text)
    except Exception as exc:
        logger.error("Prediction failed: %s", exc)
        return {"category": "error", "confidence": 0.0}
