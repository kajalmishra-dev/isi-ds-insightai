"""InsightAI operations dashboard (Streamlit)."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(
    page_title="InsightAI",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_PREFIX = f"{BASE_URL}/api/v1"
REQUEST_TIMEOUT = float(os.getenv("API_TIMEOUT_SECONDS", "20"))
CATEGORY_LABELS = {"needs_review": "Needs Review"}
TRIAGE_CATEGORIES = ("billing", "technical", "shipping", "service")
SECTIONS = ("Overview", "Review Queue", "Complaint Explorer", "Live Classification")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #1d1d1f;
            --muted: #6e6e73;
            --faint: #86868b;
            --line: rgba(0,0,0,0.08);
            --surface: #ffffff;
            --canvas: #f5f5f7;
            --accent: #0071e3;
            --accent-hover: #0077ed;
            --ok-bg: #e8f8ef;
            --ok-ink: #1d7a46;
            --bad-bg: #fce8e8;
            --bad-ink: #b91c1c;
            --warn-bg: #fff6e5;
            --warn-ink: #9a6700;
            --radius: 18px;
            --radius-sm: 12px;
            --shadow: 0 2px 8px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
        }

        html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"] {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Helvetica, Arial, sans-serif !important;
            background: var(--canvas) !important;
            color: var(--ink) !important;
            -webkit-font-smoothing: antialiased;
        }

        /* Hide Streamlit chrome */
        #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="stDecoration"] { display: none !important; }

        .block-container {
            padding: 2.25rem 2rem 3.5rem !important;
            max-width: 1080px !important;
            color: var(--ink) !important;
        }

        .block-container h1, .block-container h2, .block-container h3,
        .block-container h4, .block-container p, .block-container label,
        .block-container li, .block-container span {
            color: var(--ink) !important;
        }

        .block-container [data-testid="stMarkdownContainer"] p,
        .block-container [data-testid="stMarkdownContainer"] strong {
            color: var(--ink) !important;
        }

        .block-container h3 {
            font-size: 1.75rem !important;
            font-weight: 600 !important;
            letter-spacing: -0.03em !important;
            margin: 0 0 1.25rem !important;
        }

        .block-container h4 {
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            letter-spacing: -0.02em !important;
            margin: 1.75rem 0 0.85rem !important;
        }

        /* Hero — brand first, airy */
        .hero {
            margin: 0 0 1.75rem;
            padding: 0;
            background: transparent;
            border: none;
        }

        .brand {
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.045em;
            line-height: 1.05;
            margin: 0;
            color: var(--ink) !important;
        }

        .brand span { color: var(--accent) !important; }

        .tagline {
            margin: 0.55rem 0 0;
            font-size: 1.05rem;
            font-weight: 400;
            color: var(--muted) !important;
            letter-spacing: -0.01em;
            max-width: 34rem;
            line-height: 1.45;
        }

        .section-label {
            color: var(--faint) !important;
            font-size: 0.68rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin: 1.15rem 0 0.45rem;
        }

        /* KPI strip — Apple metrics */
        .kpi-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 0.5rem;
        }

        .kpi {
            background: var(--surface) !important;
            border: 1px solid var(--line);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 1.15rem 1.2rem 1.05rem;
            color: var(--ink) !important;
            min-height: 108px;
        }

        .kpi .label {
            color: var(--faint) !important;
            font-size: 0.72rem;
            font-weight: 500;
            letter-spacing: 0.01em;
            margin-bottom: 0.45rem;
        }

        .kpi .value {
            font-size: 2rem;
            font-weight: 600;
            letter-spacing: -0.04em;
            line-height: 1.1;
            color: var(--ink) !important;
        }

        .kpi .hint {
            color: var(--muted) !important;
            font-size: 0.78rem;
            margin-top: 0.4rem;
            letter-spacing: -0.01em;
        }

        .insight-list {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            margin-bottom: 0.25rem;
        }

        .insight-card {
            border: none;
            border-bottom: 1px solid var(--line);
            border-radius: 0;
            padding: 1rem 1.2rem;
            margin: 0;
            background: transparent !important;
            color: var(--ink) !important;
            font-size: 0.95rem;
            line-height: 1.5;
            letter-spacing: -0.01em;
        }

        .insight-card:last-child { border-bottom: none; }

        .panel {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 1.15rem 1.2rem;
            margin-bottom: 0.75rem;
        }

        .panel-title {
            font-size: 0.95rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin: 0 0 0.85rem;
            color: var(--ink) !important;
        }

        .rank-item {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            padding: 0.65rem 0;
            border-bottom: 1px solid var(--line);
            color: var(--ink) !important;
            font-size: 0.92rem;
        }

        .rank-item:last-child { border-bottom: none; }

        .rank-item .count {
            color: var(--muted) !important;
            font-variant-numeric: tabular-nums;
            font-size: 0.85rem;
        }

        .empty-state {
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 2rem 1.4rem;
            color: var(--muted) !important;
            text-align: center;
            background: var(--surface) !important;
            box-shadow: var(--shadow);
            letter-spacing: -0.01em;
        }

        .empty-state strong {
            display: block;
            color: var(--ink) !important;
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 0.35rem;
        }

        .kpi.warn {
            border-color: #f59e0b;
            background: #fffbeb !important;
        }

        .kpi.warn .value { color: #b45309 !important; }

        .kpi.critical {
            border-color: #f87171;
            background: #fef2f2 !important;
        }

        .kpi.critical .value { color: #b91c1c !important; }

        .alert-banner {
            border: 1px solid #fecaca;
            background: #fef2f2 !important;
            color: #991b1b !important;
            border-radius: var(--radius-sm);
            padding: 0.95rem 1.1rem;
            margin: 0.75rem 0 1rem;
            font-size: 0.95rem;
            line-height: 1.45;
        }

        .alert-banner.elevated {
            border-color: #fcd34d;
            background: #fffbeb !important;
            color: #92400e !important;
        }

        .review-banner {
            border: 1px solid #fcd34d;
            background: #fffbeb !important;
            color: #92400e !important;
            border-radius: var(--radius-sm);
            padding: 0.95rem 1.1rem;
            margin-bottom: 1rem;
            font-size: 0.92rem;
            line-height: 1.45;
        }

        .detail-card {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 1.25rem 1.35rem;
            margin-top: 0.75rem;
            color: var(--ink) !important;
        }

        .detail-card .meta {
            color: var(--muted) !important;
            font-size: 0.85rem;
            margin-top: 0.75rem;
        }

        /* Sidebar — soft Apple settings */
        section[data-testid="stSidebar"] {
            background: #fbfbfd !important;
            border-right: 1px solid var(--line) !important;
        }

        section[data-testid="stSidebar"] > div {
            background: #fbfbfd !important;
            padding-top: 1.25rem !important;
        }

        section[data-testid="stSidebar"] * {
            color: var(--ink) !important;
        }

        section[data-testid="stSidebar"] .section-label {
            color: var(--faint) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stCaption"],
        section[data-testid="stSidebar"] small {
            color: var(--muted) !important;
        }

        section[data-testid="stSidebar"] .stButton > button {
            background: var(--accent) !important;
            border: none !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            border-radius: 980px !important;
            padding: 0.45rem 1rem !important;
            box-shadow: none !important;
            transition: background 0.15s ease;
        }

        section[data-testid="stSidebar"] .stButton > button:hover {
            background: var(--accent-hover) !important;
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea,
        section[data-testid="stSidebar"] [data-baseweb="input"] {
            background: #ffffff !important;
            color: var(--ink) !important;
            border-radius: 10px !important;
        }

        section[data-testid="stSidebar"] .sidebar-brand {
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin: 0 0 0.15rem;
            color: var(--ink) !important;
        }

        .block-container .stButton > button {
            border: 1px solid var(--line) !important;
            color: var(--ink) !important;
            background: var(--surface) !important;
            border-radius: 980px !important;
            font-weight: 500 !important;
            box-shadow: var(--shadow);
        }

        .block-container .stButton > button[kind="primary"] {
            background: var(--accent) !important;
            border: none !important;
            color: #ffffff !important;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.28rem 0.7rem;
            border-radius: 980px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: -0.01em;
        }

        .status-pill::before {
            content: "";
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: currentColor;
        }

        .ok { background: var(--ok-bg) !important; color: var(--ok-ink) !important; }
        .bad { background: var(--bad-bg) !important; color: var(--bad-ink) !important; }
        .warn { background: var(--warn-bg) !important; color: var(--warn-ink) !important; }

        div[data-testid="stDataFrame"],
        div[data-testid="stDataFrame"] * {
            font-size: 0.88rem !important;
        }

        [data-testid="stMetricValue"] {
            font-weight: 600 !important;
            letter-spacing: -0.03em !important;
        }

        @media (max-width: 900px) {
            .kpi-row { grid-template-columns: repeat(2, 1fr); }
            .block-container { padding: 1.25rem 1rem 2rem !important; }
            .brand { font-size: 2rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "analytics_data": None,
        "complaints_data": None,
        "complaints_meta": {},
        "review_data": None,
        "jobs_data": [],
        "api_key": os.getenv("API_KEY", ""),
        "last_error": None,
        "active_job_id": None,
        "bootstrapped": False,
        "section": "Overview",
        "model_version": None,
        "loading": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def api_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    key = st.session_state.get("api_key", "")
    if key:
        headers["X-API-Key"] = key
    return headers


def api_get(path: str, params: dict[str, Any] | None = None) -> requests.Response:
    return requests.get(
        f"{API_PREFIX}{path}",
        params=params,
        headers=api_headers(),
        timeout=REQUEST_TIMEOUT,
    )


def api_post(path: str, **kwargs: Any) -> requests.Response:
    return requests.post(
        f"{API_PREFIX}{path}",
        headers=api_headers(),
        timeout=REQUEST_TIMEOUT,
        **kwargs,
    )


def check_backend() -> tuple[bool, str, str | None]:
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        ready = requests.get(f"{BASE_URL}/ready", timeout=5)
        if health.status_code != 200:
            return False, "Health check failed", None
        payload = ready.json() if ready.status_code == 200 else {}
        if payload.get("status") != "ready":
            return False, payload.get("detail") or "API not ready", None
        return True, "Connected", payload.get("model_version")
    except requests.RequestException as exc:
        return False, str(exc), None


def friendly_http_error(prefix: str, response: requests.Response) -> str:
    try:
        detail = response.json().get("detail")
    except Exception:
        detail = response.text[:240]
    if isinstance(detail, list):
        detail = "; ".join(str(item) for item in detail)
    return f"{prefix} ({response.status_code}): {detail or 'Unexpected error'}"


def load_dashboard_data(explorer_params: dict | None = None) -> None:
    st.session_state.loading = True
    try:
        summary_res = api_get("/analytics/summary")
        params = {
            "page": 1,
            "page_size": 50,
            "sort_by": "created_at",
            "sort_order": "desc",
        }
        if explorer_params:
            params.update({k: v for k, v in explorer_params.items() if v not in (None, "")})
        st.session_state.explorer_params = dict(params)

        complaints_res = api_get("/complaints", params=params)
        review_res = api_get(
            "/complaints",
            params={
                "needs_review": True,
                "page": 1,
                "page_size": 50,
                "sort_by": "confidence",
                "sort_order": "asc",
            },
        )
        jobs_res = api_get("/jobs", params={"limit": 10})
    except requests.RequestException as exc:
        st.session_state.last_error = (
            "Could not reach the API. Confirm the backend is running and API_BASE_URL is correct."
            f" Details: {exc}"
        )
        st.session_state.loading = False
        return

    if summary_res.status_code != 200:
        st.session_state.last_error = friendly_http_error("Analytics unavailable", summary_res)
        st.session_state.loading = False
        return
    if complaints_res.status_code != 200:
        st.session_state.last_error = friendly_http_error("Complaints unavailable", complaints_res)
        st.session_state.loading = False
        return

    st.session_state.analytics_data = summary_res.json()
    payload = complaints_res.json()
    items = payload.get("items", [])
    st.session_state.complaints_data = pd.DataFrame(items)
    st.session_state.complaints_meta = {
        "total": payload.get("total", len(items)),
        "page": payload.get("page", 1),
        "page_size": payload.get("page_size", len(items)),
        "total_pages": payload.get("total_pages", 1),
    }

    if review_res.status_code == 200:
        st.session_state.review_data = pd.DataFrame(review_res.json().get("items", []))
    else:
        st.session_state.review_data = pd.DataFrame()

    st.session_state.jobs_data = jobs_res.json() if jobs_res.status_code == 200 else []
    st.session_state.last_error = None
    st.session_state.loading = False


def label_category(value: str | None) -> str:
    if not value:
        return "Unknown"
    if value in CATEGORY_LABELS:
        return CATEGORY_LABELS[value]
    return str(value).replace("_", " ").title()


def format_confidence(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def format_when(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return "—"
    return ts.strftime("%b %d, %Y · %I:%M %p")


def format_job_id(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    text = str(value).strip()
    if text in {"", "None", "nan", "NaT"}:
        return "—"
    return text[:8]


def render_kpi(label: str, value: str, hint: str = "", tone: str = "") -> str:
    cls = f"kpi {tone}".strip()
    return (
        f'<div class="{cls}"><div class="label">{label}</div>'
        f'<div class="value">{value}</div><div class="hint">{hint}</div></div>'
    )


def empty_state(title: str, body: str) -> None:
    st.markdown(
        f'<div class="empty-state"><strong>{title}</strong>{body}</div>',
        unsafe_allow_html=True,
    )


def style_review_frame(df: pd.DataFrame) -> pd.DataFrame:
    view = df.copy()
    if "confidence" in view.columns:
        view["confidence"] = view["confidence"].map(format_confidence)
    if "category" in view.columns:
        view["category"] = view["category"].map(label_category)
    if "created_at" in view.columns:
        view["created_at"] = view["created_at"].map(format_when)
    if "job_id" in view.columns:
        view["job_id"] = view["job_id"].map(format_job_id)
    cols = [c for c in ["text", "category", "confidence", "created_at", "job_id"] if c in view.columns]
    return view[cols]


def render_job_panel() -> None:
    if not st.session_state.active_job_id:
        return

    try:
        job_res = api_get(f"/jobs/{st.session_state.active_job_id}")
    except requests.RequestException:
        st.warning("Could not poll job status. Check API connectivity.")
        return

    if job_res.status_code != 200:
        st.error(friendly_http_error("Job status unavailable", job_res))
        return

    job = job_res.json()
    status = job.get("status", "unknown")
    total = int(job.get("total_rows") or 0)
    processed = int(job.get("processed_rows") or 0)
    skipped = int(job.get("skipped_rows") or 0)
    errors = int(job.get("error_rows") or 0)
    pct = float(job.get("progress_percentage") or 0.0)

    st.write(f"Status: **{status}**")
    st.caption(f"Job ID `{st.session_state.active_job_id}`")
    st.progress(min(1.0, pct / 100.0 if total or status == "completed" else 0.05))
    st.caption(
        f"{pct:.0f}% · {processed} processed · {skipped} skipped · {errors} errors"
        + (f" · {total} total" if total else "")
    )

    if status == "completed":
        st.success("Analysis completed successfully.")
        quality_raw = job.get("quality_summary")
        if quality_raw:
            try:
                quality = json.loads(quality_raw)
                st.caption(
                    "Data quality — "
                    f"missing text: {quality.get('missing_text', 0)}, "
                    f"invalid timestamps: {quality.get('invalid_timestamps', 0)}, "
                    f"duplicates: {quality.get('duplicate_rows', 0)}, "
                    f"prediction errors: {quality.get('prediction_errors', 0)}"
                )
            except json.JSONDecodeError:
                pass
        load_dashboard_data()
        st.session_state.active_job_id = None
        st.session_state.section = "Overview"
        st.rerun()
    elif status == "failed":
        st.error(job.get("error_message") or "Analysis failed.")
    else:
        st.info("Processing complaints…")
        time.sleep(1.5)
        st.rerun()


def render_overview(data: dict[str, Any]) -> None:
    review_rate = float(data.get("low_confidence_rate") or 0)
    review_tone = "critical" if review_rate >= 80 else ("warn" if review_rate >= 40 else "")
    avg_hours = data.get("avg_resolution_hours")
    med = data.get("median_resolution_hours")

    kpis = "".join(
        [
            render_kpi("Total Complaints", str(data["total_complaints"]), "All ingested records"),
            render_kpi(
                "Resolved < 24h",
                f"{data['north_star_metric']}%",
                f"{data.get('within_24h_count', 0)} within SLA",
            ),
            render_kpi(
                "Needs Review",
                str(data.get("needs_review_count", 0)),
                f"{review_rate:.0f}% of total",
                tone=review_tone,
            ),
            render_kpi(
                "Median Resolution",
                f"{med:.1f}h" if med is not None else "—",
                f"Avg {avg_hours:.1f}h" if avg_hours is not None else "Resolution time",
            ),
        ]
    )
    st.markdown(f'<div class="kpi-row">{kpis}</div>', unsafe_allow_html=True)

    insights = data.get("insights") or []
    for item in insights:
        code = item.get("code", "")
        css = "alert-banner elevated" if code == "elevated_review" else "alert-banner"
        if code in {"insufficient_data"}:
            css = "alert-banner elevated"
        st.markdown(
            f'<div class="{css}">{item.get("text", item)}</div>',
            unsafe_allow_html=True,
        )

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.markdown(
            '<div class="panel"><div class="panel-title">Category distribution</div>',
            unsafe_allow_html=True,
        )
        cat_df = pd.DataFrame(
            list(data["category_distribution"].items()),
            columns=["Category", "Percentage"],
        )
        if cat_df.empty:
            empty_state("No categories", "Upload and process a CSV to see distribution.")
        else:
            cat_df["Category"] = cat_df["Category"].map(label_category)
            fig = px.bar(
                cat_df,
                x="Percentage",
                y="Category",
                orientation="h",
                text="Percentage",
                color_discrete_sequence=["#0071e3"],
            )
            fig.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside",
                textfont_color="#1d1d1f",
                marker_line_width=0,
                width=0.55,
            )
            fig.update_layout(
                margin=dict(l=10, r=40, t=10, b=10),
                xaxis_title="",
                yaxis_title="",
                showlegend=False,
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                font=dict(
                    color="#1d1d1f",
                    size=13,
                    family="-apple-system, BlinkMacSystemFont, Helvetica",
                ),
                xaxis=dict(
                    gridcolor="#f0f0f2",
                    zeroline=False,
                    range=[0, max(100, float(cat_df["Percentage"].max()) * 1.15)],
                ),
                yaxis=dict(gridcolor="#ffffff"),
                height=max(260, 56 * len(cat_df) + 80),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown(
            '<div class="panel"><div class="panel-title">Top issues</div>',
            unsafe_allow_html=True,
        )
        if not data.get("top_issues"):
            empty_state("No ranked issues", "Insights appear after complaints are classified.")
        else:
            rows = "".join(
                f'<div class="rank-item"><span>{label_category(item["category"])}</span>'
                f'<span class="count">{item["count"]}</span></div>'
                for item in data["top_issues"]
            )
            st.markdown(rows, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            '<div class="panel"><div class="panel-title">Recent jobs</div>',
            unsafe_allow_html=True,
        )
        jobs = st.session_state.jobs_data or []
        if not jobs:
            empty_state("No jobs yet", "Start an upload from the sidebar to create a job.")
        else:
            jobs_df = pd.DataFrame(jobs)
            keep = [
                c
                for c in ["id", "filename", "status", "processed_rows", "error_rows", "total_rows"]
                if c in jobs_df.columns
            ]
            display = jobs_df[keep].copy()
            if "id" in display.columns:
                display["id_short"] = display["id"].astype(str).str.slice(0, 8)
                show = display.drop(columns=["id"]).rename(columns={"id_short": "id"})
            else:
                show = display
            st.dataframe(show, use_container_width=True, hide_index=True)

            job_ids = [str(j.get("id")) for j in jobs if j.get("id")]
            selected_job = st.selectbox(
                "Job actions",
                options=job_ids,
                format_func=lambda jid: next(
                    (
                        f"{str(j.get('id', ''))[:8]} · {j.get('status')} · {j.get('filename')}"
                        for j in jobs
                        if str(j.get("id")) == jid
                    ),
                    jid,
                ),
            )
            selected_meta = next(j for j in jobs if str(j.get("id")) == selected_job)
            a1, a2 = st.columns(2)
            with a1:
                try:
                    export_res = api_get(f"/jobs/{selected_job}/export.csv")
                    if export_res.status_code == 200:
                        st.download_button(
                            "Export job CSV",
                            data=export_res.content,
                            file_name=f"insightai_job_{selected_job[:8]}.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                    else:
                        st.caption("Export unavailable for this job.")
                except requests.RequestException:
                    st.caption("Export request failed.")
            with a2:
                if selected_meta.get("can_retry") or selected_meta.get("status") == "failed":
                    if st.button("Retry failed job", use_container_width=True):
                        try:
                            retry_res = api_post(f"/jobs/{selected_job}/retry")
                        except requests.RequestException as exc:
                            st.error(f"Retry failed: {exc}")
                        else:
                            if retry_res.status_code in (200, 202):
                                st.session_state.active_job_id = selected_job
                                st.success("Retry queued")
                                st.rerun()
                            else:
                                st.error(friendly_http_error("Retry failed", retry_res))
        st.markdown("</div>", unsafe_allow_html=True)

    s1, s2, s3 = st.columns(3)
    s1.metric("Within 24h", data.get("within_24h_count", 0))
    s2.metric("Unresolved", data.get("unresolved_count", 0))
    s3.metric("24h SLA", f"{data.get('north_star_metric', 0)}%")


def render_review_queue(data: dict[str, Any]) -> None:
    count = int(data.get("needs_review_count") or 0)
    st.markdown(
        f"""
        <div class="review-banner">
            <strong>{count} pending review</strong> — confidence below threshold.
            Approve or reclassify to clear the queue.
        </div>
        """,
        unsafe_allow_html=True,
    )

    review_df = st.session_state.review_data
    if review_df is None or review_df.empty:
        empty_state(
            "Review queue is empty",
            "No items need review right now.",
        )
        return

    if "review_selected_id" not in st.session_state:
        st.session_state.review_selected_id = int(review_df.iloc[0]["id"])

    ids = [int(x) for x in review_df["id"].tolist()]
    if st.session_state.review_selected_id not in ids:
        st.session_state.review_selected_id = ids[0]

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.caption(f"{len(review_df)} shown · lowest confidence first")
        st.dataframe(style_review_frame(review_df), use_container_width=True, hide_index=True)
        st.session_state.review_selected_id = st.selectbox(
            "Select row to triage",
            options=ids,
            index=ids.index(st.session_state.review_selected_id),
            format_func=lambda cid: str(
                review_df.loc[review_df["id"] == cid, "text"].iloc[0]
            )[:90],
        )

    row = review_df.loc[review_df["id"] == st.session_state.review_selected_id].iloc[0]
    with right:
        st.markdown("**Triage**")
        st.write(row.get("text", ""))
        st.caption(
            f"Suggested: **{label_category(row.get('category'))}** · "
            f"{format_confidence(row.get('confidence'))} · "
            f"Job {format_job_id(row.get('job_id'))}"
        )
        options = list(TRIAGE_CATEGORIES)
        current = str(row.get("category") or "billing")
        if current not in options:
            options = [current] + options
        chosen = st.selectbox(
            "Assign category",
            options=options,
            index=options.index(current),
            format_func=label_category,
        )
        if st.button("Approve / Submit", type="primary", use_container_width=True):
            try:
                res = api_post(
                    f"/complaints/{int(row['id'])}/review",
                    json={"category": chosen},
                )
            except requests.RequestException as exc:
                st.error(f"Review failed: {exc}")
            else:
                if res.status_code == 200:
                    st.success("Cleared from review queue")
                    load_dashboard_data()
                    st.rerun()
                else:
                    st.error(friendly_http_error("Review failed", res))


def render_explorer(data: dict[str, Any]) -> None:
    saved = st.session_state.get("explorer_params") or {}
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        search_q = st.text_input(
            "Search text",
            value=str(saved.get("search") or ""),
            placeholder="e.g. invoice",
        )
    with f2:
        category_options = ["(all)"] + sorted(
            {label_category(c) for c in (data.get("category_distribution") or {})}
        )
        saved_cat = saved.get("category")
        cat_label = label_category(saved_cat) if saved_cat else "(all)"
        cat_index = category_options.index(cat_label) if cat_label in category_options else 0
        category_q = st.selectbox("Category", options=category_options, index=cat_index)
    with f3:
        review_options = ["(all)", "yes", "no"]
        saved_review = saved.get("needs_review")
        if saved_review is True:
            review_default = "yes"
        elif saved_review is False:
            review_default = "no"
        else:
            review_default = "(all)"
        review_q = st.selectbox(
            "Needs Review",
            options=review_options,
            index=review_options.index(review_default),
        )
    with f4:
        sort_options = ["created_at", "confidence", "category", "id"]
        sort_default = saved.get("sort_by", "created_at")
        sort_index = sort_options.index(sort_default) if sort_default in sort_options else 0
        sort_q = st.selectbox("Sort by", options=sort_options, index=sort_index)

    reverse_map = {
        label_category(c): c for c in (data.get("category_distribution") or {})
    }

    def _explorer_filters(page: int = 1) -> dict[str, Any]:
        return {
            "search": search_q.strip() or None,
            "category": None
            if category_q == "(all)"
            else reverse_map.get(category_q, category_q),
            "needs_review": None if review_q == "(all)" else review_q == "yes",
            "sort_by": sort_q,
            "sort_order": "desc",
            "page": page,
            "page_size": int(saved.get("page_size") or 50),
        }

    if st.button("Apply filters"):
        load_dashboard_data(_explorer_filters(page=1))
        st.rerun()

    export_params = {
        "search": search_q.strip() or None,
        "category": None
        if category_q == "(all)"
        else reverse_map.get(category_q, category_q),
        "needs_review": None if review_q == "(all)" else review_q == "yes",
    }
    export_params = {k: v for k, v in export_params.items() if v not in (None, "")}
    try:
        export_res = api_get("/complaints/export.csv", params=export_params or None)
        if export_res.status_code == 200:
            st.download_button(
                "Export filtered CSV",
                data=export_res.content,
                file_name="insightai_complaints.csv",
                mime="text/csv",
            )
    except requests.RequestException:
        st.caption("Could not prepare filtered export.")

    df = st.session_state.complaints_data
    meta = st.session_state.get("complaints_meta") or {}
    if df is None or df.empty:
        empty_state("No matching complaints", "Adjust filters or upload a dataset.")
        return

    view = df.copy()
    if "confidence" in view.columns:
        view["confidence"] = view["confidence"].map(format_confidence)
    if "category" in view.columns:
        view["category_label"] = view["category"].map(label_category)
    if "created_at" in view.columns:
        view["created_at"] = view["created_at"].map(format_when)
    if "resolved_at" in view.columns:
        view["resolved_at"] = view["resolved_at"].map(format_when)
    if "job_id" in view.columns:
        view["job_id"] = view["job_id"].map(format_job_id)

    show_cols = [
        c
        for c in ["text", "category_label", "confidence", "created_at", "resolved_at", "job_id"]
        if c in view.columns
    ]
    page = int(meta.get("page", 1) or 1)
    total_pages = max(1, int(meta.get("total_pages", 1) or 1))
    st.caption(
        f"Page {page} / {total_pages} · "
        f"{meta.get('total', len(view))} matching"
    )

    display = view[show_cols].rename(columns={"category_label": "category"})
    if "needs_review" in view.columns:
        flags = view["needs_review"].fillna(False).astype(bool)

        def _highlight(row: pd.Series) -> list[str]:
            return (
                ["background-color: #fff6e5"] * len(row)
                if bool(flags.loc[row.name])
                else [""] * len(row)
            )

        st.dataframe(display.style.apply(_highlight, axis=1), use_container_width=True, hide_index=True)
    else:
        st.dataframe(display, use_container_width=True, hide_index=True)

    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("← Previous", disabled=page <= 1, use_container_width=True):
            load_dashboard_data(_explorer_filters(page=page - 1))
            st.rerun()
    with nav3:
        if st.button("Next →", disabled=page >= total_pages, use_container_width=True):
            load_dashboard_data(_explorer_filters(page=page + 1))
            st.rerun()


def render_live_classify() -> None:
    samples = {
        "Billing error": "I was charged twice for the same subscription invoice.",
        "Late delivery": "My package is still in transit and the ETA keeps slipping.",
        "Account locked": "I cannot reset my password and the OTP never arrives.",
        "App crash": "The mobile app freezes right after the latest update.",
    }
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        st.caption("Predictions show model confidence, not absolute certainty.")
        st.text_area(
            "Complaint text",
            height=140,
            placeholder="Describe the issue…",
            key="live_classify_text",
        )
        chips = st.columns(len(samples))
        for col, (label, text) in zip(chips, samples.items()):
            with col:
                if st.button(label, use_container_width=True):
                    st.session_state.live_classify_text = text
                    st.rerun()
        run = st.button("Classify", type="primary", use_container_width=True)

    with right:
        if not run or not str(st.session_state.get("live_classify_text", "")).strip():
            empty_state("Prediction", "Enter text or tap a sample, then Classify.")
            return
        with st.spinner("Classifying…"):
            try:
                pred = api_post(
                    "/predict",
                    json={"text": str(st.session_state.live_classify_text).strip()},
                )
            except requests.RequestException as exc:
                st.error(f"Classification request failed: {exc}")
                return

        if pred.status_code != 200:
            st.error(friendly_http_error("Classification failed", pred))
            return

        body = pred.json()
        label = label_category(body["category"])
        if body.get("needs_review"):
            st.warning(f"**{label}** — flagged for human review")
        else:
            st.success(f"**{label}**")
        st.metric("Confidence", format_confidence(body.get("confidence")))
        st.caption(f"Model `{body.get('model_version', 'unknown')}`")
        alts = body.get("alternatives") or []
        if alts:
            st.caption(
                "Alternatives: "
                + ", ".join(f"{a['category']} {a['confidence']:.0%}" for a in alts[:3])
            )


# --- App ---
inject_styles()
init_state()

st.markdown(
    """
    <div class="hero">
        <p class="brand">Insight<span>AI</span></p>
        <p class="tagline">Complaint intelligence — classify, review, and track resolution SLAs.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

polling = bool(st.session_state.active_job_id)
if polling:
    ok, detail, model_version = True, "Connected", st.session_state.model_version
else:
    ok, detail, model_version = check_backend()
    if model_version:
        st.session_state.model_version = model_version

with st.sidebar:
    st.markdown('<p class="sidebar-brand">InsightAI</p>', unsafe_allow_html=True)
    st.caption("Complaint intelligence")

    st.markdown('<div class="section-label">System</div>', unsafe_allow_html=True)
    st.caption(f"API `{BASE_URL}`")
    if ok:
        st.markdown('<span class="status-pill ok">API ready</span>', unsafe_allow_html=True)
        if st.session_state.model_version:
            st.caption(f"Model `{st.session_state.model_version}`")
    else:
        st.markdown('<span class="status-pill bad">API down</span>', unsafe_allow_html=True)
        st.caption(detail)

    st.markdown('<div class="section-label">Authentication</div>', unsafe_allow_html=True)
    st.session_state.api_key = st.text_input(
        "API key",
        value=st.session_state.api_key,
        type="password",
        help="Required only when AUTH_ENABLED=true.",
        label_visibility="collapsed",
        placeholder="API key (optional)",
    )

    st.markdown('<div class="section-label">Data</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload dataset", type=["csv"])
    if uploaded_file is not None and st.button("Start ingestion", use_container_width=True):
        with st.spinner("Uploading dataset…"):
            try:
                res = api_post(
                    "/upload",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")},
                )
            except requests.RequestException as exc:
                st.error(f"Upload failed: {exc}")
            else:
                if res.status_code in (200, 202):
                    payload = res.json()
                    st.session_state.active_job_id = payload.get("job_id")
                    if payload.get("deduplicated"):
                        st.info("Identical file already processed — opened existing job.")
                    else:
                        st.success("Upload accepted")
                else:
                    st.error(friendly_http_error("Upload failed", res))

    render_job_panel()

    st.markdown('<div class="section-label">Analysis</div>', unsafe_allow_html=True)
    st.session_state.section = st.radio(
        "Section",
        options=SECTIONS,
        index=SECTIONS.index(st.session_state.section)
        if st.session_state.section in SECTIONS
        else 0,
        label_visibility="collapsed",
    )

    st.markdown('<div class="section-label">Configuration</div>', unsafe_allow_html=True)
    if st.button("Refresh dashboard", use_container_width=True):
        with st.spinner("Refreshing…"):
            load_dashboard_data()
        st.rerun()

if not st.session_state.bootstrapped and ok and not polling:
    with st.spinner("Loading dashboard…"):
        load_dashboard_data()
    st.session_state.bootstrapped = True

if st.session_state.last_error:
    st.error(st.session_state.last_error)

if not ok and st.session_state.analytics_data is None:
    empty_state(
        "Backend unavailable",
        "Start the API (`uvicorn backend.main:app --reload`) then click Refresh dashboard.",
    )
    st.stop()

data = st.session_state.analytics_data
if data is None:
    empty_state(
        "No analytics loaded",
        "Upload `data/sample_upload.csv` from the sidebar, or click Refresh dashboard.",
    )
    st.stop()

if st.session_state.loading:
    st.info("Loading…")

section = st.session_state.section
st.markdown(f"### {section}")

if section == "Overview":
    render_overview(data)
elif section == "Review Queue":
    render_review_queue(data)
elif section == "Complaint Explorer":
    render_explorer(data)
else:
    render_live_classify()
