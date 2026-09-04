"""Compare candidate classifiers on a fixed holdout split.

Selection criterion (in order):
1. macro F1
2. weighted F1
3. accuracy

Does not invent metrics — only reports measured holdout performance.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.svm import LinearSVC

from ml.preprocess import normalize_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = os.path.join("data", "complaints.csv")
MODEL_DIR = os.path.join("ml", "artifacts")
EXPERIMENT_PATH = os.path.join(MODEL_DIR, "experiments.json")
RANDOM_STATE = 42

os.makedirs(MODEL_DIR, exist_ok=True)


def load_xy():
    df = pd.read_csv(DATA_PATH)
    df = df.dropna(subset=["text", "category"])
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"] != ""]
    return df["text"], df["category"]


def _normalize_batch(texts):
    return [normalize_text(t) for t in texts]


def _tfidf(**kwargs) -> TfidfVectorizer:
    defaults = {
        "ngram_range": (1, 2),
        "min_df": 1,
        "max_df": 0.95,
        "sublinear_tf": True,
        "lowercase": True,
    }
    defaults.update(kwargs)
    return TfidfVectorizer(**defaults)


def candidate_pipelines() -> dict[str, Pipeline]:
    """Named candidate recipes. All must support predict_proba."""
    normalize = FunctionTransformer(_normalize_batch, validate=False)

    return {
        "tfidf-logreg-v2": Pipeline(
            [
                ("tfidf", _tfidf()),
                (
                    "clf",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        solver="lbfgs",
                    ),
                ),
            ]
        ),
        "tfidf-logreg-norm-v3": Pipeline(
            [
                ("normalize", normalize),
                ("tfidf", _tfidf()),
                (
                    "clf",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        solver="lbfgs",
                        C=2.0,
                    ),
                ),
            ]
        ),
        "tfidf-logreg-c05-v3": Pipeline(
            [
                ("normalize", normalize),
                ("tfidf", _tfidf(ngram_range=(1, 2), min_df=1)),
                (
                    "clf",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        solver="lbfgs",
                        C=0.5,
                    ),
                ),
            ]
        ),
        "tfidf-linearsvc-calibrated-v3": Pipeline(
            [
                ("normalize", normalize),
                ("tfidf", _tfidf()),
                (
                    "clf",
                    CalibratedClassifierCV(
                        LinearSVC(class_weight="balanced", max_iter=5000),
                        method="sigmoid",
                        cv=2,
                    ),
                ),
            ]
        ),
        "tfidf-multinomialnb-v3": Pipeline(
            [
                ("normalize", normalize),
                ("tfidf", _tfidf()),
                ("clf", MultinomialNB(alpha=0.5)),
            ]
        ),
    }


def evaluate_candidates(random_state: int = RANDOM_STATE) -> dict:
    features, labels = load_xy()
    stratify = labels if labels.value_counts().min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.2,
        random_state=random_state,
        stratify=stratify,
    )

    rows = []
    fitted = {}
    for name, pipeline in candidate_pipelines().items():
        logger.info("Evaluating candidate: %s", name)
        pipeline.fit(x_train, y_train)
        preds = pipeline.predict(x_test)
        row = {
            "model": name,
            "macro_f1": float(f1_score(y_test, preds, average="macro", zero_division=0)),
            "weighted_f1": float(
                f1_score(y_test, preds, average="weighted", zero_division=0)
            ),
            "accuracy": float(accuracy_score(y_test, preds)),
            "notes": _notes_for(name),
        }
        rows.append(row)
        fitted[name] = pipeline
        logger.info(
            "%s -> macro_f1=%.3f weighted_f1=%.3f accuracy=%.3f",
            name,
            row["macro_f1"],
            row["weighted_f1"],
            row["accuracy"],
        )

    ranked = sorted(
        rows,
        key=lambda r: (r["macro_f1"], r["weighted_f1"], r["accuracy"]),
        reverse=True,
    )
    winner_name = ranked[0]["model"]
    baseline = next(r for r in rows if r["model"] == "tfidf-logreg-v2")
    winner = ranked[0]
    improved = (
        winner["macro_f1"] > baseline["macro_f1"] + 1e-9
        or (
            abs(winner["macro_f1"] - baseline["macro_f1"]) <= 1e-9
            and winner["weighted_f1"] > baseline["weighted_f1"] + 1e-9
        )
    )

    payload = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "selection_rule": ["macro_f1", "weighted_f1", "accuracy"],
        "holdout_rows": int(len(x_test)),
        "train_rows": int(len(x_train)),
        "random_state": random_state,
        "baseline": baseline["model"],
        "winner": winner_name,
        "improved_over_baseline": improved,
        "results": ranked,
        "caveats": [
            "All scores are from one stratified holdout on a small synthetic dataset.",
            "A higher score here is not proof of production NLP quality.",
            "Winner is adopted only when measured metrics improve (or tie-break).",
        ],
    }

    with open(EXPERIMENT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    logger.info(
        "Winner: %s (improved_over_baseline=%s)",
        winner_name,
        improved,
    )
    return {
        "report": payload,
        "winner_name": winner_name,
        "winner_pipeline": fitted[winner_name],
        "x_train": x_train,
        "x_test": x_test,
        "y_train": y_train,
        "y_test": y_test,
        "features": features,
        "labels": labels,
    }


def _notes_for(name: str) -> str:
    notes = {
        "tfidf-logreg-v2": "Baseline TF-IDF + LogisticRegression",
        "tfidf-logreg-norm-v3": "Normalized text + LogReg C=2.0",
        "tfidf-logreg-c05-v3": "Normalized text + stronger regularization C=0.5",
        "tfidf-linearsvc-calibrated-v3": "LinearSVC with sigmoid calibration for probabilities",
        "tfidf-multinomialnb-v3": "Multinomial Naive Bayes on TF-IDF",
    }
    return notes.get(name, "")


if __name__ == "__main__":
    result = evaluate_candidates()
    print(json.dumps(result["report"], indent=2))
