import json
from pathlib import Path

import pandas as pd


def test_train_and_held_out_are_disjoint():
    train = pd.read_csv("data/complaints.csv")
    sample = pd.read_csv("data/sample_upload.csv")
    train_texts = set(train["text"].str.casefold())
    sample_texts = set(sample["text"].str.casefold())
    assert train_texts.isdisjoint(sample_texts)
    assert "category" not in sample.columns
    assert {"text", "created_at", "resolved_at"}.issubset(sample.columns)


def test_generated_timestamps_are_ordered():
    for path in ("data/complaints.csv", "data/sample_upload.csv"):
        df = pd.read_csv(path)
        created = pd.to_datetime(df["created_at"])
        resolved = pd.to_datetime(df["resolved_at"])
        assert (resolved >= created).all(), path


def test_metadata_evaluation_and_experiments_exist():
    meta = Path("ml/artifacts/metadata.json")
    evaluation = Path("ml/artifacts/evaluation.json")
    experiments = Path("ml/artifacts/experiments.json")
    assert meta.exists(), "Run python -m ml.train before tests in CI"
    assert evaluation.exists()
    assert experiments.exists()

    payload = json.loads(meta.read_text(encoding="utf-8"))
    report = json.loads(evaluation.read_text(encoding="utf-8"))
    experiment = json.loads(experiments.read_text(encoding="utf-8"))

    assert payload["model_version"] == experiment["winner"]
    assert report["model_version"] == payload["model_version"]
    assert "macro_f1" in payload
    assert "confusion_matrix" in report
    assert "results" in experiment
    assert len(experiment["results"]) >= 2
    # Winner must be best by selection rule
    ranked = experiment["results"]
    assert ranked[0]["model"] == experiment["winner"]
    assert ranked[0]["macro_f1"] >= ranked[-1]["macro_f1"]


def test_predict_includes_model_version(client, monkeypatch):
    monkeypatch.setattr(
        "backend.services.ingestion.predict",
        lambda _text: {
            "category": "billing",
            "confidence": 0.9,
            "model_version": "tfidf-logreg-norm-v3",
            "alternatives": [{"category": "service", "confidence": 0.05}],
        },
    )
    response = client.post("/api/v1/predict", json={"text": "Double charged"})
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "tfidf-logreg-norm-v3"
    assert body["alternatives"][0]["category"] == "service"


def test_normalize_text_basic():
    from ml.preprocess import normalize_text

    assert normalize_text("  Hello, WORLD!!  ") == "hello world"
