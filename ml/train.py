"""Train the selected InsightAI classifier and write eval artifacts."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import joblib
from sklearn.metrics import classification_report, confusion_matrix

from ml.experiments import EXPERIMENT_PATH, evaluate_candidates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join("ml", "artifacts")
MODEL_PATH = os.path.join(MODEL_DIR, "model.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "metadata.json")
EVAL_PATH = os.path.join(MODEL_DIR, "evaluation.json")

os.makedirs(MODEL_DIR, exist_ok=True)


def train():
    experiment = evaluate_candidates()
    model = experiment["winner_pipeline"]
    model_version = experiment["winner_name"]
    x_test = experiment["x_test"]
    y_test = experiment["y_test"]
    x_train = experiment["x_train"]
    features = experiment["features"]
    labels = experiment["labels"]

    predictions = model.predict(x_test)
    report = classification_report(
        y_test, predictions, output_dict=True, zero_division=0
    )
    logger.info("\n%s", classification_report(y_test, predictions, zero_division=0))

    labels_sorted = sorted(labels.unique().tolist())
    cm = confusion_matrix(y_test, predictions, labels=labels_sorted)
    class_counts = labels.value_counts().to_dict()

    # Ensure probabilities exist for product confidence UX
    if not hasattr(model, "predict_proba"):
        raise RuntimeError(
            f"Selected model {model_version} does not support predict_proba"
        )

    joblib.dump(model, MODEL_PATH)

    evaluation = {
        "model_version": model_version,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "holdout_rows": int(len(x_test)),
        "train_rows": int(len(x_train)),
        "accuracy": report["accuracy"],
        "macro_precision": report["macro avg"]["precision"],
        "macro_recall": report["macro avg"]["recall"],
        "macro_f1": report["macro avg"]["f1-score"],
        "weighted_f1": report["weighted avg"]["f1-score"],
        "per_class": {
            label: {
                "precision": report[label]["precision"],
                "recall": report[label]["recall"],
                "f1": report[label]["f1-score"],
                "support": report[label]["support"],
            }
            for label in labels_sorted
            if label in report
        },
        "confusion_matrix": {
            "labels": labels_sorted,
            "matrix": cm.astype(int).tolist(),
        },
        "experiment_path": EXPERIMENT_PATH,
        "improved_over_baseline": experiment["report"]["improved_over_baseline"],
        "caveats": [
            "Metrics are from a stratified holdout of a small synthetic dataset.",
            "Macro F1 on ~20 test rows is informative for demos, not production quality.",
            "Model confidence is the max class probability and may be poorly calibrated.",
            "Model chosen by ml/experiments.py using macro F1 (then weighted F1, accuracy).",
        ],
    }
    with open(EVAL_PATH, "w", encoding="utf-8") as handle:
        json.dump(evaluation, handle, indent=2)

    metadata = {
        "model_version": model_version,
        "model_path": MODEL_PATH,
        "evaluation_path": EVAL_PATH,
        "experiment_path": EXPERIMENT_PATH,
        "classes": labels_sorted,
        "class_counts": {k: int(v) for k, v in class_counts.items()},
        "dataset_rows": int(len(features)),
        "train_rows": int(len(x_train)),
        "holdout_rows": int(len(x_test)),
        "macro_f1": report["macro avg"]["f1-score"],
        "accuracy": report["accuracy"],
        "improved_over_baseline": experiment["report"]["improved_over_baseline"],
        "candidates_evaluated": [row["model"] for row in experiment["report"]["results"]],
        "dataset_notes": (
            "Synthetic hand-authored complaints from scripts/generate_training_data.py. "
            "sample_upload.csv is a held-out text set with zero overlap."
        ),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    logger.info(
        "Saved %s -> %s (macro_f1=%.3f, accuracy=%.3f, improved=%s)",
        model_version,
        MODEL_PATH,
        metadata["macro_f1"],
        metadata["accuracy"],
        metadata["improved_over_baseline"],
    )
    return metadata, evaluation


if __name__ == "__main__":
    train()
