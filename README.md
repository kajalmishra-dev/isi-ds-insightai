# InsightAI

Complaint intelligence platform: CSV in → ML classify → review queue → SLA analytics.

**Stack:** FastAPI · Streamlit · scikit-learn (`tfidf-logreg-v2`) · SQLAlchemy · SQLite  
**Version:** 2.1.0

---

## Live demo

| Surface | URL |
|---------|-----|
| **Dashboard** | [https://insightai-ui.onrender.com](https://insightai-ui.onrender.com) |
| **API** | [https://insightai-api.onrender.com](https://insightai-api.onrender.com) |
| **API docs** | [https://insightai-api.onrender.com/docs](https://insightai-api.onrender.com/docs) |
| **Health** | [https://insightai-api.onrender.com/health](https://insightai-api.onrender.com/health) |
| **Source** | [github.com/kajalmishra-dev/isi-ds-insightai](https://github.com/kajalmishra-dev/isi-ds-insightai) |

> Free-tier hosts sleep after idle. First request after sleep can take ~30–60s.

### Quick demo

1. Open the [dashboard](https://insightai-ui.onrender.com) - wait for **Online** in the sidebar  
2. Download **sample CSV** from the sidebar (or use `data/sample_upload.csv`)  
3. Upload → watch the job finish  
4. Check **Overview**, triage **Review Queue**, try **Live Classification**

---

## What it does

- Async CSV ingestion with job progress, idempotent content-hash reuse, and retry  
- TF-IDF + Logistic Regression classification with confidence → **Needs Review**  
- Clear winners (top-1 vs top-2 margin) skip review even when max-prob is soft  
- Ops dashboard: KPIs, category mix, SLA (% resolved in 24h), explorer + CSV export  
- Human triage (Approve / Reject) with feedback counted for retraining  
- Optional API-key auth, CORS, request IDs, `/health` + `/ready`

---

## Architecture

```
Browser  →  Streamlit UI  →  FastAPI /api/v1
                                │
                   ┌────────────┼────────────┐
                   ▼            ▼            ▼
              ML (joblib)   SQLite DB   Background jobs
```

Hosted on Render (`render.yaml`): `insightai-api` + `insightai-ui`.

---

## Local run

```bash
pip install -r requirements-dev.txt
# model artifacts ship in ml/artifacts/ - retrain only if needed:
#   python scripts/generate_training_data.py && python -m ml.train
uvicorn backend.main:app --reload
# other terminal
streamlit run frontend/app.py
```

| Local | URL |
|-------|-----|
| Dashboard | http://127.0.0.1:8501 |
| API docs | http://127.0.0.1:8000/docs |

**Docker:**

```bash
docker compose up --build
```

Staging with auth:

```powershell
$env:API_KEY="replace-me"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

Reset junk local data: `python scripts/reset_local_db.py` → restart → upload `data/sample_upload.csv`.

---

## API (v1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/ready` | DB + model ready |
| POST | `/api/v1/upload` | CSV → job (`202`, or `200` if duplicate content) |
| GET | `/api/v1/jobs/{id}` | Job status |
| GET | `/api/v1/jobs` | Recent jobs |
| POST | `/api/v1/jobs/{id}/retry` | Retry failed job |
| GET | `/api/v1/analytics/summary` | KPIs + insights |
| GET | `/api/v1/complaints` | Filter / search / paginate |
| GET | `/api/v1/complaints/export.csv` | Export |
| POST | `/api/v1/predict` | Classify one text |
| POST | `/api/v1/complaints/{id}/review` | Human triage |

CSV columns: `text`, `created_at`, `resolved_at`

Auth (optional): `AUTH_ENABLED=true` + `API_KEY` → header `X-API-Key`.

---

## Configuration

Copy `.env.example` → `.env`.

| Variable | Purpose |
|----------|---------|
| `AUTH_ENABLED` / `API_KEY` | Protect `/api/v1/*` |
| `REQUIRE_AUTH_IN_PRODUCTION` | Force auth when `ENVIRONMENT=production\|staging` |
| `CONFIDENCE_THRESHOLD` | Soft max-prob review cutoff (default `0.32`) |
| `CONFIDENCE_MARGIN` | Clear winner margin to skip review (default `0.10`) |
| `API_BASE_URL` | Frontend → API (Render UI uses the public API URL) |

---

## Deploy (Render)

Blueprint: [`render.yaml`](./render.yaml)

1. Push `main` to GitHub  
2. Render → **New** → **Blueprint** → this repo  
3. Apply → wait for `insightai-api` + `insightai-ui`  
4. Open the UI URL above  

UI must set `API_BASE_URL=https://insightai-api.onrender.com`.  
SQLite on free instances is ephemeral (redeploy clears demo data).

---

## ML notes

- Synthetic training data (`data/complaints.csv`, 240 rows) - not customer data  
- Demo upload (`data/sample_upload.csv`, 48 rows) is **held out** (no train overlap)  
- Winner selected via holdout macro-F1 (`ml/artifacts/experiments.json`)  
- Soft probabilities (~0.3–0.5) on a 4-class logreg are expected  

```bash
pytest tests/ -v
```

---

## Layout

```
backend/     FastAPI, auth, jobs, analytics
frontend/    Streamlit ops dashboard
ml/          Train / infer + committed artifacts
data/        Train + sample upload CSVs
docs/        Feature guide PDF
scripts/     Data + helper scripts
tests/       API / ML / product contracts
```

---

## Limitations

- In-process jobs (not a durable worker queue)  
- SQLite default (Postgres on the roadmap)  
- Free Render sleep + cold start  
- Metrics are demo-scale, not production customer performance  

---

## License

Private / portfolio project unless otherwise noted.
