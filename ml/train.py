import logging
import os
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = "data/complaints.csv"
MODEL_DIR = "ml/artifacts"

os.makedirs(MODEL_DIR, exist_ok=True)


def load_data():
    logger.info("Loading dataset...")
    df = pd.read_csv(DATA_PATH)

    if "text" not in df.columns or "category" not in df.columns:
        raise ValueError("Dataset must contain 'text' and 'category' columns")

    return df["text"], df["category"]


def build_pipeline():
    logger.info("Building ML pipeline...")

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=200))
    ])

    return pipeline


def train():
    X, y = load_data()

    model = build_pipeline()

    logger.info("Training model...")
    model.fit(X, y)

    model_path = os.path.join(MODEL_DIR, "model.joblib")

    logger.info("Saving model...")
    joblib.dump(model, model_path)

    logger.info(f"Model saved at {model_path}")


if __name__ == "__main__":
    train()