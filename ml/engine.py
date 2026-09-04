import json
import logging
import os
from pathlib import Path

import joblib
import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join("ml", "artifacts", "model.joblib")
METADATA_PATH = os.path.join("ml", "artifacts", "metadata.json")
DEFAULT_MODEL_VERSION = "unknown"


class ModelEngine:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise RuntimeError(
                f"Model not found at {MODEL_PATH}. Run: python -m ml.train"
            )

        logger.info("Loading model from %s", MODEL_PATH)
        self.model = joblib.load(MODEL_PATH)
        self.metadata = self._load_metadata()
        self.model_version = self.metadata.get("model_version", DEFAULT_MODEL_VERSION)

    @staticmethod
    def _load_metadata() -> dict:
        path = Path(METADATA_PATH)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read model metadata: %s", exc)
            return {}

    def predict(self, text: str):
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        probs = self.model.predict_proba([text])[0]
        classes = self.model.classes_
        max_idx = int(np.argmax(probs))
        ranked = sorted(
            (
                {"category": str(classes[i]), "confidence": float(probs[i])}
                for i in range(len(classes))
            ),
            key=lambda item: item["confidence"],
            reverse=True,
        )

        return {
            "category": str(classes[max_idx]),
            "confidence": float(probs[max_idx]),
            "model_version": self.model_version,
            "alternatives": ranked[1:3],
        }


_engine = None


def get_engine() -> ModelEngine:
    global _engine
    if _engine is None:
        _engine = ModelEngine()
    return _engine


def get_model_version() -> str:
    try:
        return get_engine().model_version
    except Exception:
        path = Path(METADATA_PATH)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8")).get(
                    "model_version", DEFAULT_MODEL_VERSION
                )
            except (OSError, json.JSONDecodeError):
                return DEFAULT_MODEL_VERSION
        return DEFAULT_MODEL_VERSION


def predict(text: str):
    """Classify text. Raises on model/load/inference failure (does not swallow)."""
    return get_engine().predict(text)
