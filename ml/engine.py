import logging
import joblib
import numpy as np
import os

# ======================
# LOGGING
# ======================
logger = logging.getLogger(__name__)

# ======================
# PATH
# ======================
MODEL_PATH = os.path.join("ml", "artifacts", "model.joblib")


class ModelEngine:
    def __init__(self):
        try:
            logger.info("Loading model...")
            self.model = joblib.load(MODEL_PATH)
            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error(f"Model loading failed: {str(e)}")
            raise RuntimeError("Failed to load ML model")

    def predict(self, text: str):
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        try:
            probs = self.model.predict_proba([text])[0]
            classes = self.model.classes_

            max_idx = int(np.argmax(probs))

            category = classes[max_idx]
            confidence = float(probs[max_idx])

            return {
                "category": category,
                "confidence": confidence
            }

        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            return {
                "category": "error",
                "confidence": 0.0
            }


# ======================
# SINGLETON INSTANCE
# ======================
engine = ModelEngine()


def predict(text: str):
    return engine.predict(text)