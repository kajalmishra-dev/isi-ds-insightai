import logging
import os
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


# LOGGING
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = os.path.join("data", "complaints.csv")
MODEL_DIR = os.path.join("ml", "artifacts")
MODEL_PATH = os.path.join(MODEL_DIR, "model.joblib")

os.makedirs(MODEL_DIR, exist_ok=True)


# LOAD DATA
def load_data():
    logger.info("Loading dataset...")

    df = pd.read_csv(DATA_PATH)

    required_cols = {"text", "category"}
    if not required_cols.issubset(df.columns):
        raise ValueError("Dataset must contain 'text' and 'category' columns")

    # CLEAN DATA
    df = df.dropna(subset=["text", "category"])
    df["text"] = df["text"].astype(str)

    return df["text"], df["category"]


# BUILD PIPELINE
def build_pipeline():
    logger.info("Building ML pipeline...")

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
        ("clf", LogisticRegression(
            class_weight="balanced",
            max_iter=300
        ))
    ])

    return pipeline


# TRAIN MODEL
def train():
    X, y = load_data()

    # TRAIN/TEST SPLIT
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = build_pipeline()

    logger.info("Training model...")
    model.fit(X_train, y_train)

    # EVALUATION
    logger.info("Evaluating model...")
    preds = model.predict(X_test)

    report = classification_report(y_test, preds)
    logger.info(f"\n{report}")

    # SAVE MODEL
    logger.info("Saving model...")
    joblib.dump(model, MODEL_PATH)

    logger.info(f"Model saved at {MODEL_PATH}")


# RUN
if __name__ == "__main__":
    train()