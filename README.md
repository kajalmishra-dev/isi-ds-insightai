# 📊 InsightAI

> **AI-powered customer complaint classification and analytics**

InsightAI is a full-stack machine learning application that ingests raw customer complaint data, automatically classifies it using NLP, and surfaces actionable insights through an interactive dashboard — including a **North Star Metric** tracking how many complaints are resolved within 24 hours.

Designed as a production-style pipeline integrating ML inference with real-time analytics.

---

## ✨ Features

- 📁 **CSV Upload** — drag-and-drop complaint data via the Streamlit UI
- 🤖 **ML Classification** — TF-IDF + Logistic Regression pipeline with confidence scoring
- 📊 **Analytics Dashboard** — category distribution, top issues, drill-down by category
- ⚡ **North Star Metric** — % of complaints resolved within 24 hours
- 🔄 **Background Processing** — large uploads handled asynchronously via FastAPI
- 🗄️ **Persistent Storage** — SQLite (dev) or PostgreSQL (prod) via SQLAlchemy

---

## 🏗️ Architecture

```
┌─────────────────┐        HTTP        ┌──────────────────────┐
│  Streamlit UI   │ ◄────────────────► │  FastAPI Backend     │
│   (app.py)      │                    │  /api/v1/...         │
└─────────────────┘                    └──────────┬───────────┘
                                                  │
                              ┌───────────────────┼───────────────────┐
                              │                   │                   │
                    ┌─────────▼──────┐  ┌─────────▼──────┐  ┌───────▼───────┐
                    │   ML Engine    │  │   SQLAlchemy   │  │   Analytics   │
                    │  (engine.py)   │  │  ORM + SQLite  │  │ (analytics.py)│
                    └────────────────┘  └────────────────┘  └───────────────┘
```

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Train the model

```bash
# Your training CSV needs: text, category columns
python -m ml.train --data data/complaints.csv
```

### 3. Start the backend

```bash
uvicorn main:app --reload
```

### 4. Start the frontend

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## 📁 Project Structure

```
insightai/
                     # Streamlit frontend
├── app.py                     # FastAPI app entry point
├── backend/
│   ├── main.py 
│   ├── api/
│   │   └── routes.py           # API endpoints
│   ├── core/
│   │   ├── database.py         # SQLAlchemy engine & session
│   │   └── deps.py             # FastAPI dependencies
│   ├── models/
│   │   └── complaint.py        # SQLAlchemy ORM model
│   ├── schemas/
│   │   └── complaint.py        # Pydantic request/response schemas
│   └── services/
│       └── analytics.py        # Analytics query logic
├── ml/
│   ├── engine.py               # Model inference (singleton)
│   ├── train.py                # Model training script
│   └── artifacts/              # Saved model files (gitignored)
└── data/                       # CSV uploads (gitignored)
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload a complaints CSV |
| `GET` | `/analytics/summary` | Aggregated analytics + North Star |
| `GET` | `/api/v1/complaints?limit=50&offset=0` | Paginated complaints list |
| `GET` | `/health` | Health check |

Full interactive docs available at http://localhost:8000/docs (Swagger UI).

---

## ⚙️ Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./insight.db` | SQLAlchemy connection string |

For PostgreSQL: `export DATABASE_URL=postgresql://user:pass@localhost:5432/insightai`

---

## 🧠 ML Model

- **Algorithm:** Logistic Regression with `class_weight="balanced"`
- **Features:** TF-IDF with unigrams and bigrams (`ngram_range=(1,2)`)
- **Evaluation:** Basic train-test validation

---

## 🔮 Future Enhancements

- [ ] LLM-based classification (OpenAI / local models)
- [ ] Real-time processing via WebSockets
- [ ] User authentication (Admin / Analyst roles)
- [ ] Cloud deployment (Docker + Railway / Render)
- [ ] Email/Slack alerts on complaint spikes

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit, Plotly |
| Backend | FastAPI, Uvicorn |
| ML | scikit-learn, joblib |
| Database | SQLAlchemy, SQLite / PostgreSQL |
| Data | Pandas |

## 🧩 Key Engineering Highlights

- End-to-end pipeline: ingestion → ML → storage → analytics
- Separation of concerns (API, services, ML engine)
- Background processing for scalability
- Designed for easy extension to distributed systems (Celery, Redis)
