# Reproduce InsightAI locally

## 1. Install

```bash
pip install -r requirements-dev.txt
```

## 2. Build training data + model

```bash
python scripts/generate_training_data.py
python -m ml.train
```

Writes:

- `data/complaints.csv` — labeled training set
- `data/sample_upload.csv` — **held-out** upload sample (no text overlap with training)
- `ml/artifacts/model.joblib`
- `ml/artifacts/metadata.json` (includes selected `model_version`)
- `ml/artifacts/evaluation.json` (macro F1, confusion matrix, caveats)
- `ml/artifacts/experiments.json` (candidate comparison table)

## 3. Configure (optional)

```bash
copy .env.example .env
```

The API loads `.env` automatically on startup. Existing shell environment
variables take precedence over the file.

If `AUTH_ENABLED=true`, you must set a non-empty `API_KEY` or the app will
refuse to start.

## 4. Run API

```bash
uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000/docs

## 5. Run dashboard

```bash
streamlit run frontend/app.py
```

Open http://127.0.0.1:8501  

### Sample workflow

1. Confirm sidebar shows **API ready**
2. Upload `data/sample_upload.csv`
3. Wait for job completion (progress + data-quality summary)
4. Check Overview KPIs / insights and Review Queue
5. Export a job CSV from Overview → Job actions
6. Optionally retry a failed job if you force a model failure

## 6. Tests

```bash
pytest tests/ -v
```

## Docker

```bash
docker compose up --build
```

Notes:

- Model is trained during image build and kept inside the image.
- Database/uploads persist via Docker volume `insightai_data`.
- Frontend talks to the API at `http://api:8000`.
