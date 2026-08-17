import json
import logging
import os

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = os.path.join("data", "complaints.csv")
MODEL_DIR = os.path.join("ml", "artifacts")
MODEL_PATH = os.path.join(MODEL_DIR, "model.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "metadata.json")

os.makedirs(MODEL_DIR, exist_ok=True)


def load_data():
    logger.info("Loading dataset from %s", DATA_PATH)
    df = pd.read_csv(DATA_PATH)

    required_cols = {"text", "category"}
    if not required_cols.issubset(df.columns):
        raise ValueError("Dataset must contain 'text' and 'category' columns")

    df = df.dropna(subset=["text", "category"])
    df["text"] = df["text"].astype(str)
    return df["text"], df["category"]


def build_pipeline():
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=300)),
        ]
    )


def train():
    features, labels = load_data()
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42
    )

    model = build_pipeline()
    logger.info("Training model...")
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    report = classification_report(y_test, predictions, output_dict=True)
    logger.info("\n%s", classification_report(y_test, predictions))

    joblib.dump(model, MODEL_PATH)
    metadata = {
        "model_path": MODEL_PATH,
        "classes": sorted(labels.unique().tolist()),
        "train_rows": int(len(features)),
        "macro_f1": report["macro avg"]["f1-score"],
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    logger.info("Model saved to %s", MODEL_PATH)


if __name__ == "__main__":
    train()
