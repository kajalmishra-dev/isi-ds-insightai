# InsightAI - Complaint Intelligence Platform

Production-style system for complaint ingestion, ML classification, review queues, SLA analytics, export, and job retry.

**Version:** 2.1 · FastAPI + Streamlit + scikit-learn + SQLAlchemy

---

## What you get

- CSV upload with **async job tracking** (progress, processed/skipped/error counts, data-quality summary)
- **Content-hash idempotency** (identical uploads reuse the existing job)
- **Retry** for failed jobs when the source file is still available
- ML classification with **confidence threshold → Needs Review**
- Analytics KPIs + **computed insights** (never hardcoded fake observations)
- Complaint explorer with search/sort/filters + **CSV export**
- Live classify with `model_version` + alternative scores
- Sidebar **sample CSV download** + **feature guide PDF** for demos
- Optional **API key auth**, CORS, request IDs, response timing, readiness probes
- Docker Compose deployment with persisted DB/uploads volume

---

## Architecture

```
Streamlit dashboard  ──HTTP──►  FastAPI /api/v1
                                  │
                    ┌─────────────┼──────────────┐
                    ▼             ▼              ▼
               ML engine     SQLite (default)   Ingestion jobs
               (joblib)      SQLAlchemy         (background)
```

Postgres is a roadmap item - the running stack defaults to SQLite.

---

## Quick start

```bash
pip install -r requirements-dev.txt
python scripts/generate_training_data.py
python -m ml.train
uvicorn backend.main:app --reload
# other terminal
streamlit run frontend/app.py
```

- API docs: http://127.0.0.1:8000/docs  
- Dashboard: http://127.0.0.1:8501  
- Sample upload file: `data/sample_upload.csv` (**48 held-out texts** - use this in the UI)
- Feature guide PDF: `docs/InsightAI_Feature_Guide.pdf` (also downloadable from the sidebar)
- Training labels live in `data/complaints.csv` (**240 rows**, 60×4) - for `python -m ml.train` only, not for demo upload
- If the dashboard shows junk / 100% review from old runs: stop API → `python scripts/reset_local_db.py` → restart → upload `sample_upload.csv`

### Sample workflow

1. Open the dashboard and confirm **API ready**
2. Upload `data/sample_upload.csv`
3. Watch job progress (processed / skipped / errors)
4. Review KPIs, AI insights, and the **Review Queue**
5. Export a job CSV or filtered complaints CSV
6. Try live classification on a single complaint

---

## API (v1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/ready` | DB + model readiness (+ `model_version`) |
| POST | `/api/v1/upload` | Accept CSV → `job_id` (`202`, or `200` if identical content already ingested) |
| GET | `/api/v1/jobs/{id}` | Job status |
| GET | `/api/v1/jobs` | Recent jobs |
| POST | `/api/v1/jobs/{id}/retry` | Retry a **failed** job |
| GET | `/api/v1/jobs/{id}/export.csv` | Download classified rows for a job |
| GET | `/api/v1/analytics/summary` | KPIs + computed insights |
| GET | `/api/v1/complaints` | Paginated list (`page`, `page_size`, `category`, `search`, `sort_by`, `sort_order`, `date_from`, `date_to`, `needs_review`, confidence bounds) |
| GET | `/api/v1/complaints/export.csv` | Download filtered complaints |
| POST | `/api/v1/predict` | Classify one text |

Legacy flat paths (`/upload`, `/complaints`, …) still work for compatibility.

Response headers include `X-Request-ID` and `X-Response-Time-Ms`.

### Upload CSV columns

```
text, created_at, resolved_at
```

### Auth

```bash
# .env
AUTH_ENABLED=true
API_KEY=replace-with-a-long-secret
```

Send header: `X-API-Key: <key>`

---

## Configuration

Copy `.env.example` to `.env`. The API loads it automatically via `python-dotenv`
(process environment variables still win if already set).

Important flags:

| Variable | Purpose |
|----------|---------|
| `AUTH_ENABLED` | Require `X-API-Key` on `/api/v1/*` |
| `API_KEY` | Required when auth is enabled (fail-fast if missing) |
| `REQUIRE_AUTH_IN_PRODUCTION` | Defaults **true** - `ENVIRONMENT=production\|staging` must enable auth (opt out only for demos) |
| `CONFIDENCE_THRESHOLD` | Soft max-prob cutoff for Needs Review (default `0.32`) |
| `CONFIDENCE_MARGIN` | Clear winners (top1-top2 ≥ this) auto-accept even below threshold (default `0.10`) |

See `.env.example` for `DATABASE_URL`, upload limits, CORS, page sizes, and frontend `API_BASE_URL`.

---

## Tests

```bash
pytest tests/ -v
```

---

## Docker

```bash
docker compose up --build
```

Shared / staging (auth required):

```bash
# Windows PowerShell
$env:API_KEY="replace-me"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

- Frontend uses `API_BASE_URL=http://api:8000` (Compose DNS - not localhost).
- ML model is **baked into the image** at build time. Do not mount an empty
  host `ml/artifacts` over it (that previously wiped the model on fresh clones).
- SQLite DB + uploads persist in the named volume `insightai_data`.
- Compose defaults to `ENVIRONMENT=development` with auth off for local demos.
  Production overlay sets `AUTH_ENABLED=true` and requires `API_KEY`.

---

## Deploy on Render (public URL)

Blueprint file: `render.yaml` (API + Streamlit UI on free web services).

1. Push this repo to GitHub (branch `main`)
2. Open [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
3. Connect `kajalmishra-dev/isi-ds-insightai` and apply the blueprint
4. Wait for both services to build (first build trains the model - several minutes)
5. Open the **insightai-ui** URL (e.g. `https://insightai-ui.onrender.com`)

Notes:

- Demo auth is off (`REQUIRE_AUTH_IN_PRODUCTION=false`). Turn on `AUTH_ENABLED` + `API_KEY` for a shared/staging audience.
- Free tier sleeps when idle - the first hit after sleep can take about a minute.
- SQLite on free instances is ephemeral (redeploy resets demo data).

---

## Project layout

```
backend/     FastAPI app, auth, jobs, analytics, export
frontend/    Streamlit operations dashboard
ml/          Training, experiments, inference
data/        Training + held-out sample upload CSVs
scripts/     Data generation helpers
tests/       API / ML / product contract tests
```

---

## ML pipeline

Classifier is selected by measured holdout comparison (`python -m ml.experiments`
via `python -m ml.train`).

- Training data is **synthetic / hand-authored** (`scripts/generate_training_data.py`).
- Demo upload file `data/sample_upload.csv` is a **held-out** text set (zero overlap with training texts).
- Candidate comparison is written to `ml/artifacts/experiments.json`.
- Holdout metrics for the winner are in `ml/artifacts/evaluation.json`.
- Selection rule: highest **macro F1**, then weighted F1, then accuracy.
- We only claim improvement when those measured metrics beat the baseline.
- Predictions below `CONFIDENCE_THRESHOLD` set `needs_review=true`, unless top-1 beats top-2 by `CONFIDENCE_MARGIN` (clear winner)
  while keeping the model’s predicted `category` (so charts stay meaningful).
- Reviewers can clear the queue with `POST /api/v1/complaints/{id}/review`.
- 4-class logistic regression max-probabilities are often soft (~0.3–0.5); that is expected,
  not a broken upload. Prefer `data/sample_upload.csv` for demos.
- API responses expose `model_version` and optional alternative class scores. Model confidence is the max class probability and may be poorly calibrated.

---

## Known limitations

- In-process background jobs (not a durable worker queue)
- SQLite by default (Postgres on the roadmap)
- Small synthetic dataset - do not treat metrics as customer-data performance
- Re-uploading the **exact same file bytes** returns the existing job (content-hash idempotency). A changed file creates a new job.
- Startup reclaim marks abandoned `processing` jobs as `failed` after a crash/restart.
- Job API never exposes server filesystem paths; use `can_retry` to know if retry is possible.

---

## Roadmap

- Swap classical ML for transformer/LLM classifiers behind the same API
- Postgres + Alembic migrations for multi-instance deploys
- Object storage for uploads + worker queue (RQ/Celery)
- Role-based access (viewer / analyst / admin)
