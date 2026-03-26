# 📊 InsightAI — AI Complaint Intelligence System

> End-to-end ML-powered system for complaint classification, storage, and analytics with a real-world business metric.

---

## What This Project Does

InsightAI ingests raw complaint data via CSV, classifies each complaint using an ML model, stores results in a database, and generates actionable analytics through an interactive dashboard.

It is designed as a **production-style pipeline** combining:

* FastAPI (backend)
* Streamlit (frontend)
* ML inference (scikit-learn)
* Background processing

---

## Key Features

* 📁 **CSV Upload Pipeline**

  * Upload complaint data via UI
  * Processed asynchronously in background

* 🤖 **ML Classification**

  * TF-IDF + Logistic Regression
  * Confidence-based predictions
  * Low confidence → `needs_review`

* 🗄️ **Database Storage**

  * SQLAlchemy ORM
  * SQLite (dev), PostgreSQL-ready

* 📊 **Analytics Dashboard**

  * Category distribution (%)
  * Top issues
  * Drill-down filtering
  * Recent complaints view

* ⚡ **North Star Metric**

  * % of complaints resolved within **24 hours**

---

## System Architecture

```
Streamlit UI
    ↓ HTTP
FastAPI Backend
    ↓
 ┌───────────────┬───────────────┬───────────────┐
 │               │               │               │
ML Engine     Database        Analytics     Background Task
(engine.py)   (SQLAlchemy)    (services)    (CSV ingestion)
```

---

## Data Flow

1. User uploads CSV via Streamlit
2. FastAPI saves file
3. Background task:

   * Reads CSV using Pandas
   * Runs ML predictions
   * Applies confidence threshold
   * Stores in DB
4. Analytics API computes:

   * category distribution
   * resolution metrics
5. Streamlit displays dashboard

---

## ML Pipeline

* **Vectorizer:** TF-IDF (1–2 grams)
* **Model:** Logistic Regression
* **Handling Imbalance:** `class_weight="balanced"`

**Prediction Output:**

```json
{
  "category": "payment",
  "confidence": 0.82
}
```

**Business Rule:**

* confidence < 0.6 → `needs_review`

---

## Metrics

### North Star Metric

> % of complaints resolved within 24 hours

```
(resolved within 24h / total complaints) * 100
```

### Other Metrics

* Category distribution (%)
* Top 3 issues
* Recent complaints

---

## 📁 Project Structure

```
insightai/

├── backend/
│   ├── main.py                  # FastAPI entrypoint
│   ├── api/routes.py            # Upload + analytics endpoints
│   ├── core/
│   │   ├── database.py          # DB config
│   │   └── deps.py              # DB dependency
│   ├── models/complaint.py      # ORM model
│   ├── schemas/complaint.py     # Response schemas
│   └── services/analytics.py    # Analytics logic
│
├── frontend/
│   └── app.py                   # Streamlit dashboard
│
├── ml/
│   ├── engine.py                # Model loading + prediction
│   ├── train.py                 # Training script
│   └── artifacts/model.joblib   # Saved model
│
├── data/                        # Uploaded CSVs
├── insight.db                   # SQLite database
└── README.md
```

---

## API Endpoints

| Method | Endpoint             | Description                   |
| ------ | -------------------- | ----------------------------- |
| POST   | `/upload`            | Upload CSV (async processing) |
| GET    | `/analytics/summary` | Aggregated insights           |
| GET    | `/complaints`        | Latest complaints             |
| GET    | `/health`            | Health check                  |

---

## Setup Instructions

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 2. Train model

```bash
python -m ml.train
```

---

### 3. Run backend

```bash
uvicorn backend.main:app --reload
```

---

### 4. Run frontend

```bash
streamlit run frontend/app.py
```

---

### 5. Open dashboard

```
http://localhost:8501
```

---

## Input Requirements

### Upload CSV

Must contain:

```
text, created_at, resolved_at
```

### Training CSV

Must contain:

```
text, category
```

---

## Engineering Highlights

* Clean separation: API / ML / Services / DB
* Background processing using FastAPI tasks
* Confidence-aware ML decisions
* Stateful UI using Streamlit session
* Real business metric design (North Star)

---

## Future Improvements

* Replace ML with BERT / LLM
* Add authentication (JWT)
* Pagination + filtering in backend
* Docker + cloud deployment
* Real-time streaming (Kafka/WebSockets)

---

## What This Proves

* You can build production-style ML systems
* You understand backend + ML integration
* You think in terms of metrics, not just models
* You can design scalable pipelines

---

## Author

Built as part of full-stack ISI internship.

---