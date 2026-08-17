# Reproduce InsightAI locally

## 1. Install

```bash
pip install -r requirements-dev.txt
```

## 2. Train the model

```bash
python -m ml.train
```

This uses `data/complaints.csv` and writes `ml/artifacts/model.joblib`.

## 3. Run the API

```bash
uvicorn backend.main:app --reload
```

## 4. Run the dashboard

```bash
streamlit run frontend/app.py
```

## 5. Run tests

```bash
pytest tests/ -v
```

## Docker

```bash
docker compose up --build
```
