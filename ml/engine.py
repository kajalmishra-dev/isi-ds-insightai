import logging
import joblib
import os
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = "ml/artifacts/model.joblib"


class ModelEngine:
    def __init__(self):
        logger.info("Loading model...")
        self.model = joblib.load(MODEL_PATH)

    def predict(self, text: str):
        if not text:
            raise ValueError("Input text cannot be empty")

        probs = self.model.predict_proba([text])[0]
        classes = self.model.classes_

        max_idx = np.argmax(probs)

        return {
            "category": classes[max_idx],
            "confidence": float(probs[max_idx])
        }


# Load once (singleton pattern)
engine = ModelEngine()


def predict(text: str):
    return engine.predict(text)