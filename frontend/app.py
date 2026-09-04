"""InsightAI operations dashboard (Streamlit)."""

from __future__ import annotations

import html
import json
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
CATEGORY_COLORS = {
    "Billing": "#0071e3",
    "Shipping": "#34c759",
    "Service": "#ff9f0a",
    "Technical": "#af52de",
    "Needs Review": "#ff3b30",
    "Unknown": "#8e8e93",
}
CHART_FALLBACK_COLORS = ["#0071e3", "#34c759", "#ff9f0a", "#af52de", "#5ac8fa", "#ff375f"]
REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV_PATH = REPO_ROOT / "data" / "sample_upload.csv"
FEATURE_GUIDE_PATH = REPO_ROOT / "docs" / "InsightAI_Feature_Guide.pdf"


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

        /* Hide Streamlit chrome - display:none avoids sticky blur over hero */
        #MainMenu, footer { visibility: hidden; height: 0; }
        header[data-testid="stHeader"],
        [data-testid="stHeader"],
        .stApp > header {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="stDecoration"] { display: none !important; }

        .block-container {
            padding: 1.75rem 2rem 3.5rem !important;
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

        /* Hero - brand first, airy */
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

        /* KPI strip - Apple metrics */
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
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 2rem;
            padding: 0.15rem 0.55rem;
            border-radius: 980px;
            background: #f5f5f7;
            color: var(--ink) !important;
            font-variant-numeric: tabular-nums;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .alerts-card {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 1rem 1.15rem;
            margin: 0.75rem 0 1rem;
        }

        .alerts-card .alerts-title {
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: var(--faint) !important;
            margin: 0 0 0.65rem;
        }

        .alerts-card ul {
            margin: 0;
            padding: 0;
            list-style: none;
        }

        .alerts-card li {
            display: flex;
            gap: 0.55rem;
            align-items: flex-start;
            padding: 0.4rem 0;
            border-bottom: 1px solid var(--line);
            color: var(--ink) !important;
            font-size: 0.92rem;
            line-height: 1.4;
        }

        .alerts-card li:last-child { border-bottom: none; }

        .alert-tag {
            flex: 0 0 auto;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            padding: 0.18rem 0.45rem;
            border-radius: 6px;
            margin-top: 0.1rem;
        }

        .alert-tag.warn { background: #fef3c7; color: #92400e; }
        .alert-tag.critical { background: #fee2e2; color: #991b1b; }
        .alert-tag.info { background: #e8f1ff; color: #1d4ed8; }

        .skeleton-card {
            background: var(--surface);
            border: 1px dashed #d2d2d7;
            border-radius: var(--radius);
            padding: 1.25rem 1.35rem;
            color: var(--faint) !important;
        }

        .skeleton-card .skel-label {
            height: 0.7rem;
            width: 35%;
            background: #ececef;
            border-radius: 4px;
            margin-bottom: 0.85rem;
        }

        .skeleton-card .skel-title {
            height: 1.35rem;
            width: 55%;
            background: #e5e5ea;
            border-radius: 6px;
            margin-bottom: 1rem;
        }

        .skeleton-card .skel-bar {
            height: 0.55rem;
            width: 100%;
            background: #ececef;
            border-radius: 980px;
            margin: 0.85rem 0 0.35rem;
            overflow: hidden;
        }

        .skeleton-card .skel-bar > span {
            display: block;
            height: 100%;
            width: 42%;
            background: #d2d2d7;
            border-radius: 980px;
        }

        .skeleton-card .skel-meta {
            font-size: 0.85rem;
            color: var(--muted) !important;
            margin-top: 0.75rem;
        }

        /* Live Classification - align result card with textarea label */
        .live-field-label {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--ink) !important;
            margin: 0 0 0.35rem;
            line-height: 1.4;
            min-height: 1.25rem;
        }

        .live-sample-label {
            font-size: 0.8rem;
            color: var(--muted) !important;
            margin: 0.35rem 0 0.45rem;
        }

        .prediction-card {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 1.25rem 1.35rem;
        }

        .prediction-card .pred-kicker {
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--faint) !important;
            margin: 0 0 0.55rem;
        }

        .prediction-card .pred-badge {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.45rem;
            margin: 0 0 0.35rem;
        }

        .prediction-card .pred-badge .tag {
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            padding: 0.35rem 0.85rem;
            border-radius: 980px;
            background: #e8f1ff;
            color: #1d4ed8 !important;
        }

        .prediction-card .pred-badge .tag.review {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            padding: 0.22rem 0.55rem;
            background: #fff6e5;
            color: #9a6700 !important;
        }

        .prediction-card .pred-conf {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            margin: 1rem 0 0.4rem;
        }

        .prediction-card .pred-conf .pct {
            font-size: 1.55rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            color: var(--ink) !important;
        }

        .prediction-card .pred-conf .hint {
            font-size: 0.8rem;
            color: var(--muted) !important;
        }

        .prediction-card .pred-bar {
            height: 0.55rem;
            width: 100%;
            background: #ececef;
            border-radius: 980px;
            overflow: hidden;
            margin-bottom: 1.1rem;
        }

        .prediction-card .pred-bar > span {
            display: block;
            height: 100%;
            background: var(--accent);
            border-radius: 980px;
        }

        .prediction-card .pred-alts-title {
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--muted) !important;
            margin: 0 0 0.55rem;
        }

        .prediction-card .alt-row {
            display: grid;
            grid-template-columns: 5.5rem 1fr 3.2rem;
            gap: 0.55rem;
            align-items: center;
            margin: 0.35rem 0;
            font-size: 0.85rem;
            color: var(--ink) !important;
        }

        .prediction-card .alt-row .alt-bar {
            height: 0.4rem;
            background: #ececef;
            border-radius: 980px;
            overflow: hidden;
        }

        .prediction-card .alt-row .alt-bar > span {
            display: block;
            height: 100%;
            background: #a1a1a6;
            border-radius: 980px;
        }

        .prediction-card .alt-row .alt-pct {
            text-align: right;
            color: var(--muted) !important;
            font-variant-numeric: tabular-nums;
        }

        .prediction-card .pred-model {
            margin-top: 0.9rem;
            font-size: 0.78rem;
            color: var(--faint) !important;
        }

        /* Sample chips (st.pills) - nowrap + accent hover */
        [data-testid="stPills"] button,
        [data-testid="stButtonGroup"] button {
            white-space: nowrap !important;
            cursor: pointer !important;
            transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
        }

        [data-testid="stPills"] button:hover,
        [data-testid="stButtonGroup"] button:hover {
            border-color: var(--accent) !important;
            color: var(--accent) !important;
            background: #f0f7ff !important;
        }

        .pager {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin-top: 0.65rem;
            padding-top: 0.65rem;
            border-top: 1px solid var(--line);
            color: var(--muted) !important;
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

        /* Sidebar - soft Apple settings */
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
            font-size: 1.2rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin: 0;
            color: var(--ink) !important;
            line-height: 1.2;
        }

        section[data-testid="stSidebar"] .sidebar-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            margin-bottom: 0.35rem;
        }

        section[data-testid="stSidebar"] .status-dot {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            font-size: 0.75rem;
            font-weight: 500;
            color: var(--muted) !important;
            white-space: nowrap;
        }

        section[data-testid="stSidebar"] .status-dot i {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            background: #34c759;
        }

        section[data-testid="stSidebar"] .status-dot.down i {
            background: #ff3b30;
        }

        section[data-testid="stSidebar"] .sidebar-divider {
            height: 1px;
            background: var(--line);
            margin: 1rem 0;
        }

        section[data-testid="stSidebar"] .sidebar-footer {
            margin-top: 1.25rem;
            padding-top: 0.75rem;
            border-top: 1px solid var(--line);
            font-size: 0.72rem;
            color: var(--faint) !important;
            letter-spacing: -0.01em;
        }

        /* Nav: radio → vertical pill tabs */
        section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {
            flex-direction: column;
            gap: 0.2rem;
            border: none !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 10px !important;
            padding: 0.55rem 0.7rem !important;
            margin: 0 !important;
            transition: background 0.12s ease, border-color 0.12s ease;
        }

        section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
            background: #f0f0f2 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {
            background: #ffffff !important;
            border-color: var(--line) !important;
            box-shadow: var(--shadow);
            font-weight: 600 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child {
            display: none !important;
        }

        section[data-testid="stSidebar"] .stButton > button[kind="secondary"],
        section[data-testid="stSidebar"] button[data-testid="baseButton-secondary"] {
            background: transparent !important;
            border: 1px solid var(--line) !important;
            color: var(--muted) !important;
            font-weight: 500 !important;
            padding: 0.25rem 0.55rem !important;
            min-height: 0 !important;
            font-size: 0.78rem !important;
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

        div[data-testid="stDataFrame"] [data-testid="stElementToolbar"],
        div[data-testid="stDataFrame"] [data-testid="stElementToolbarButton"],
        [data-testid="stElementToolbar"] {
            display: none !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }

        /* Selected review-queue row (glide selection + styler fallback) */
        div[data-testid="stDataFrame"] [aria-selected="true"],
        div[data-testid="stDataFrame"] [role="gridcell"][aria-selected="true"] {
            background-color: #ebf5ff !important;
        }

        .triage-complaint {
            color: var(--ink) !important;
            font-size: 0.98rem;
            line-height: 1.45;
            margin: 0 0 0.75rem;
        }

        .triage-meta {
            color: var(--muted) !important;
            font-size: 0.85rem;
            line-height: 1.4;
            margin: 0 0 1rem;
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
        return "-"


def format_when(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return "-"
    # Compact: year is implied for current ops data
    return ts.strftime("%b %d, %I:%M %p")


def format_job_id(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    text = str(value).strip()
    if text in {"", "None", "nan", "NaT"}:
        return "-"
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


def style_review_frame(df: pd.DataFrame, selected_id: int | None = None):
    """Human-readable review table; highlights the active triage row."""
    view = df.copy()
    if "confidence" in view.columns:
        view["confidence"] = (pd.to_numeric(view["confidence"], errors="coerce") * 100).round(1)
    if "category" in view.columns:
        view["category"] = view["category"].map(label_category)
    if "created_at" in view.columns:
        view["created_at"] = view["created_at"].map(format_when)
    if "job_id" in view.columns:
        view["job_id"] = view["job_id"].map(format_job_id)
    cols = [c for c in ["text", "category", "confidence", "created_at", "job_id"] if c in view.columns]
    view = view[cols].reset_index(drop=True)

    if selected_id is None or "id" not in df.columns:
        return view

    # Positional index of the selected complaint in the current queue order
    id_list = [int(x) for x in df["id"].tolist()]
    try:
        selected_pos = id_list.index(int(selected_id))
    except ValueError:
        return view

    def _highlight(row: pd.Series) -> list[str]:
        if int(row.name) == selected_pos:
            return ["background-color: #EBF5FF"] * len(row)
        return [""] * len(row)

    return view.style.apply(_highlight, axis=1)


def _alert_tag_for(code: str) -> tuple[str, str]:
    if code in {"review_overload", "sla_risk", "weakest_confidence"}:
        return "critical", "Critical"
    if code in {"elevated_review"}:
        return "warn", "Watch"
    return "info", "Info"


def render_system_alerts(insights: list[dict[str, Any]]) -> None:
    if not insights:
        return
    items = []
    for item in insights:
        code = str(item.get("code") or "")
        if code == "insufficient_data":
            continue
        tag_cls, tag_label = _alert_tag_for(code)
        text = item.get("text", item)
        items.append(
            f'<li><span class="alert-tag {tag_cls}">{tag_label}</span>'
            f"<span>{text}</span></li>"
        )
    if not items:
        return
    st.markdown(
        '<div class="alerts-card"><div class="alerts-title">System alerts</div>'
        f"<ul>{''.join(items)}</ul></div>",
        unsafe_allow_html=True,
    )


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
                    "Data quality - "
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
                f"{med:.1f}h" if med is not None else "-",
                f"Avg {avg_hours:.1f}h" if avg_hours is not None else "Resolution time",
            ),
        ]
    )
    st.markdown(f'<div class="kpi-row">{kpis}</div>', unsafe_allow_html=True)

    review_n = int(data.get("needs_review_count") or 0)
    reviewed_n = int(data.get("human_reviewed_count") or 0)
    if review_n > 0:
        go_col, feedback_col = st.columns([1.2, 1])
        with go_col:
            if st.button(
                f"Triage {review_n} pending reviews →",
                type="primary",
                use_container_width=True,
                key="goto_review_queue",
            ):
                st.session_state.section = "Review Queue"
                st.rerun()
        with feedback_col:
            if reviewed_n:
                st.caption(f"{reviewed_n} complaints human-reviewed (feedback for retraining)")
    elif reviewed_n:
        st.success(f"Queue clear - {reviewed_n} complaints human-reviewed. Nice work.")

    render_system_alerts(data.get("insights") or [])

    if int(data.get("total_complaints") or 0) == 0:
        empty_state(
            "No complaints yet",
            "Download the sample CSV from the sidebar, upload it, then explore Overview.",
        )
        return

    left, right = st.columns([1.35, 1], gap="large")
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
            total = int(data.get("total_complaints") or 0)
            counts_by_label = {
                label_category(item["category"]): int(item["count"])
                for item in (data.get("top_issues") or [])
            }
            raw_dist = data.get("category_distribution") or {}
            for raw, pct in raw_dist.items():
                label = label_category(raw)
                if label not in counts_by_label and total:
                    counts_by_label[label] = int(round(float(pct) * total / 100.0))

            cat_df["Category"] = cat_df["Category"].map(label_category)
            cat_df["Count"] = cat_df["Category"].map(
                lambda label: counts_by_label.get(label, 0)
            )
            cat_df["Axis"] = [
                f"{label} ({count}) - {pct:.1f}%"
                for label, count, pct in zip(
                    cat_df["Category"], cat_df["Count"], cat_df["Percentage"]
                )
            ]
            cat_df = cat_df.sort_values("Percentage", ascending=True)
            color_map = {
                label: CATEGORY_COLORS.get(
                    label, CHART_FALLBACK_COLORS[i % len(CHART_FALLBACK_COLORS)]
                )
                for i, label in enumerate(cat_df["Category"])
            }
            fig = px.bar(
                cat_df,
                x="Percentage",
                y="Axis",
                orientation="h",
                color="Category",
                color_discrete_map=color_map,
            )
            fig.update_traces(marker_line_width=0, width=0.62)
            fig.update_layout(
                margin=dict(l=10, r=24, t=10, b=10),
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
                    range=[0, max(100, float(cat_df["Percentage"].max()) * 1.12)],
                    ticksuffix="%",
                ),
                yaxis=dict(gridcolor="#ffffff"),
                height=max(280, 64 * len(cat_df) + 80),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            # Donut mix for a stronger dashboard feel
            pie = go.Figure(
                data=[
                    go.Pie(
                        labels=cat_df["Category"],
                        values=cat_df["Count"],
                        hole=0.58,
                        marker=dict(
                            colors=[color_map[c] for c in cat_df["Category"]],
                            line=dict(color="#ffffff", width=2),
                        ),
                        textinfo="label+percent",
                        textposition="outside",
                        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
                    )
                ]
            )
            pie.update_layout(
                margin=dict(l=10, r=10, t=8, b=8),
                showlegend=False,
                height=220,
                paper_bgcolor="#ffffff",
                font=dict(size=12, color="#1d1d1f"),
                annotations=[
                    dict(
                        text=f"<b>{total}</b><br>total",
                        x=0.5,
                        y=0.5,
                        font_size=14,
                        showarrow=False,
                    )
                ],
            )
            st.plotly_chart(pie, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown(
            '<div class="panel"><div class="panel-title">Recent Ingestion Jobs</div>',
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
            if len(job_ids) == 1:
                selected_job = job_ids[0]
            else:
                selected_job = st.selectbox(
                    "Export job",
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
            actions = st.columns(
                2
                if (selected_meta.get("can_retry") or selected_meta.get("status") == "failed")
                else 1
            )
            with actions[0]:
                try:
                    export_res = api_get(f"/jobs/{selected_job}/export.csv")
                    if export_res.status_code == 200:
                        st.download_button(
                            "Export CSV",
                            data=export_res.content,
                            file_name=f"insightai_job_{selected_job[:8]}.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                except requests.RequestException:
                    st.caption("Export unavailable")
            if selected_meta.get("can_retry") or selected_meta.get("status") == "failed":
                with actions[1]:
                    if st.button("Retry", use_container_width=True):
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




def render_review_queue(data: dict[str, Any]) -> None:
    count = int(data.get("needs_review_count") or 0)
    st.markdown(
        f"""
        <div class="review-banner">
            <strong>{count} pending review</strong> - click a table row to triage on the right.
        </div>
        """,
        unsafe_allow_html=True,
    )

    review_df = st.session_state.review_data
    if review_df is None or review_df.empty:
        st.markdown(
            """
            <div class="empty-state">
                <strong>Review queue clear</strong>
                Nothing needs human triage right now. Head back to Overview for refreshed KPIs.
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Back to Overview", type="primary", key="review_to_overview"):
            st.session_state.section = "Overview"
            load_dashboard_data()
            st.rerun()
        return

    if "review_selected_id" not in st.session_state:
        st.session_state.review_selected_id = int(review_df.iloc[0]["id"])

    ids = [int(x) for x in review_df["id"].tolist()]
    if st.session_state.review_selected_id not in ids:
        st.session_state.review_selected_id = ids[0]

    table_key = "review_queue_table"
    table_state = st.session_state.get(table_key)
    current_rows: list[int] = []
    if isinstance(table_state, dict):
        current_rows = [
            int(r)
            for r in ((table_state.get("selection") or {}).get("rows") or [])
            if isinstance(r, (int, float)) or (isinstance(r, str) and str(r).isdigit())
        ]
    # Prefer the dataframe's checkbox selection when present
    if current_rows and 0 <= current_rows[0] < len(ids):
        st.session_state.review_selected_id = ids[current_rows[0]]
    elif st.session_state.review_selected_id not in ids:
        st.session_state.review_selected_id = ids[0]

    selected_pos = ids.index(int(st.session_state.review_selected_id))
    # Seed checkbox only when nothing is selected yet (don't fight user clicks)
    if not current_rows:
        st.session_state[table_key] = {
            "selection": {"rows": [selected_pos], "columns": []}
        }

    left, right = st.columns([1.4, 1], gap="large")
    with left:
        st.markdown(
            '<div class="panel"><div class="panel-title">Review queue</div>'
            f'<div class="triage-meta">{len(review_df)} shown · lowest confidence first</div>',
            unsafe_allow_html=True,
        )
        display = style_review_frame(review_df, selected_id=st.session_state.review_selected_id)
        event = st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=table_key,
            column_config={
                "text": st.column_config.TextColumn("Complaint", width="large"),
                "category": st.column_config.TextColumn("Category", width="medium"),
                "confidence": st.column_config.ProgressColumn(
                    "Confidence",
                    help="Model confidence (max-probability)",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                    width="small",
                ),
                "created_at": st.column_config.TextColumn("Created", width="small"),
                "job_id": st.column_config.TextColumn("Job", width="small"),
            },
        )
        selected_rows = []
        if event is not None and getattr(event, "selection", None) is not None:
            selected_rows = list(event.selection.rows or [])
        if selected_rows and 0 <= selected_rows[0] < len(ids):
            st.session_state.review_selected_id = ids[selected_rows[0]]
        st.markdown("</div>", unsafe_allow_html=True)

    row = review_df.loc[review_df["id"] == st.session_state.review_selected_id].iloc[0]
    with right:
        st.markdown(
            '<div class="panel"><div class="panel-title">Triage</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p class="triage-complaint">{html.escape(str(row.get("text", "")))}</p>',
            unsafe_allow_html=True,
        )
        conf_pct = float(row.get("confidence") or 0) * 100
        conf_label = "Low" if conf_pct < 30 else ("Medium" if conf_pct < 50 else "OK")
        st.markdown(
            f'<p class="triage-meta">Suggested: <strong>{label_category(row.get("category"))}</strong> · '
            f"{format_confidence(row.get('confidence'))} ({conf_label}) · "
            f"Job {format_job_id(row.get('job_id'))}</p>",
            unsafe_allow_html=True,
        )
        options = list(TRIAGE_CATEGORIES)
        current = str(row.get("category") or "billing").strip().lower()
        if current not in options:
            options = [current] + options

        # Reset dropdown to the model's suggested category whenever the row changes
        cat_key = f"triage_cat_{int(row['id'])}"
        if st.session_state.get("triage_bound_id") != int(row["id"]):
            st.session_state[cat_key] = current
            st.session_state.triage_bound_id = int(row["id"])
        elif cat_key not in st.session_state:
            st.session_state[cat_key] = current

        chosen = st.selectbox(
            "Assign category",
            options=options,
            format_func=label_category,
            key=cat_key,
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
                    st.session_state.pop("triage_bound_id", None)
                    load_dashboard_data()
                    st.rerun()
                else:
                    st.error(friendly_http_error("Review failed", res))
        st.markdown("</div>", unsafe_allow_html=True)


def render_explorer(data: dict[str, Any]) -> None:
    saved = st.session_state.get("explorer_params") or {}
    reverse_map = {
        label_category(c): c for c in (data.get("category_distribution") or {})
    }

    export_params = {
        "search": saved.get("search"),
        "category": saved.get("category"),
        "needs_review": saved.get("needs_review"),
    }
    export_params = {k: v for k, v in export_params.items() if v not in (None, "")}

    title_col, export_col = st.columns([3.2, 1], gap="medium")
    with title_col:
        st.markdown("### Complaint Explorer")
        st.caption("Filters update automatically · Export uses the current filter set")
    with export_col:
        st.markdown('<div style="height:0.35rem"></div>', unsafe_allow_html=True)
        try:
            export_res = api_get("/complaints/export.csv", params=export_params or None)
            if export_res.status_code == 200:
                st.download_button(
                    "Export CSV",
                    data=export_res.content,
                    file_name="insightai_complaints.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="explorer_export_top",
                )
        except requests.RequestException:
            st.caption("Export unavailable")

    SORT_OPTIONS = [
        ("created_at", "Sort: Created"),
        ("confidence", "Sort: Confidence"),
        ("category", "Sort: Category"),
        ("id", "Sort: ID"),
    ]
    sort_values = [v for v, _ in SORT_OPTIONS]
    sort_labels = dict(SORT_OPTIONS)

    cat_values = ["(all)"] + sorted(
        {label_category(c) for c in (data.get("category_distribution") or {})}
    )
    saved_cat = saved.get("category")
    cat_label = label_category(saved_cat) if saved_cat else "(all)"
    cat_index = cat_values.index(cat_label) if cat_label in cat_values else 0

    review_values = ["(all)", "yes", "no"]
    review_labels = {
        "(all)": "Review: All",
        "yes": "Review: Yes",
        "no": "Review: No",
    }
    saved_review = saved.get("needs_review")
    if saved_review is True:
        review_default = "yes"
    elif saved_review is False:
        review_default = "no"
    else:
        review_default = "(all)"

    sort_default = saved.get("sort_by", "created_at")
    sort_index = sort_values.index(sort_default) if sort_default in sort_values else 0

    t1, t2, t3, t4 = st.columns([2.4, 1.2, 1.15, 1.15], gap="small")
    with t1:
        search_q = st.text_input(
            "Search",
            value=str(saved.get("search") or ""),
            placeholder="Search complaint text…",
            label_visibility="collapsed",
        )
    with t2:
        category_q = st.selectbox(
            "Category",
            options=cat_values,
            index=cat_index,
            format_func=lambda v: "Category: All" if v == "(all)" else f"Category: {v}",
            label_visibility="collapsed",
        )
    with t3:
        review_q = st.selectbox(
            "Needs Review",
            options=review_values,
            index=review_values.index(review_default),
            format_func=lambda v: review_labels[v],
            label_visibility="collapsed",
        )
    with t4:
        sort_q = st.selectbox(
            "Sort by",
            options=sort_values,
            index=sort_index,
            format_func=lambda v: sort_labels[v],
            label_visibility="collapsed",
        )

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

    current = _explorer_filters(page=int(saved.get("page") or 1))
    filter_keys = ("search", "category", "needs_review", "sort_by", "sort_order", "page_size")
    filters_changed = any(current.get(k) != saved.get(k) for k in filter_keys)
    if filters_changed:
        load_dashboard_data(_explorer_filters(page=1))
        st.rerun()

    df = st.session_state.complaints_data
    meta = st.session_state.get("complaints_meta") or {}
    if df is None or df.empty:
        empty_state("No matching complaints", "Adjust filters or upload a dataset.")
        return

    view = df.copy()
    if "confidence" in view.columns:
        view["confidence"] = (pd.to_numeric(view["confidence"], errors="coerce") * 100).round(1)
    if "category" in view.columns:
        view["category_label"] = view["category"].map(label_category)
    if "created_at" in view.columns:
        view["created_at"] = view["created_at"].map(format_when)
    if "resolved_at" in view.columns:
        view["resolved_at"] = view["resolved_at"].map(format_when)

    # job_id intentionally omitted - noise in the grid; available via API/export
    show_cols = [
        c
        for c in ["text", "category_label", "confidence", "created_at", "resolved_at"]
        if c in view.columns
    ]
    page = int(meta.get("page", 1) or 1)
    total_pages = max(1, int(meta.get("total_pages", 1) or 1))
    display = view[show_cols].rename(columns={"category_label": "category"})

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "text": st.column_config.TextColumn("Complaint", width="large"),
            "category": st.column_config.TextColumn("Category", width="medium"),
            "confidence": st.column_config.ProgressColumn(
                "Confidence",
                format="%.1f%%",
                min_value=0,
                max_value=100,
                width="small",
            ),
            "created_at": st.column_config.TextColumn("Created", width="medium"),
            "resolved_at": st.column_config.TextColumn("Resolved", width="medium"),
        },
    )

    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("← Previous", disabled=page <= 1, use_container_width=True):
            load_dashboard_data(_explorer_filters(page=page - 1))
            st.rerun()
    with nav2:
        st.markdown(
            f'<div style="text-align:center;color:#6e6e73;padding-top:0.45rem;">'
            f"Page {page} / {total_pages} · {meta.get('total', len(view))} matching</div>",
            unsafe_allow_html=True,
        )
    with nav3:
        if st.button("Next →", disabled=page >= total_pages, use_container_width=True):
            load_dashboard_data(_explorer_filters(page=page + 1))
            st.rerun()


def render_prediction_card(body: dict[str, Any]) -> None:
    label = label_category(body.get("category"))
    conf = float(body.get("confidence") or 0)
    conf_pct = conf * 100
    needs_review = bool(body.get("needs_review"))
    review_tag = (
        '<span class="tag review">Needs review</span>' if needs_review else ""
    )
    alts = body.get("alternatives") or []
    alt_rows = []
    for alt in alts[:3]:
        alt_label = label_category(alt.get("category"))
        alt_conf = float(alt.get("confidence") or 0) * 100
        alt_rows.append(
            f'<div class="alt-row">'
            f"<span>{html.escape(alt_label)}</span>"
            f'<div class="alt-bar"><span style="width:{min(100.0, alt_conf):.1f}%"></span></div>'
            f'<span class="alt-pct">{alt_conf:.1f}%</span>'
            f"</div>"
        )
    alts_html = (
        f'<div class="pred-alts-title">Also considering</div>{"".join(alt_rows)}'
        if alt_rows
        else ""
    )
    model = html.escape(str(body.get("model_version") or "unknown"))
    st.markdown(
        f"""
        <div class="prediction-card">
            <div class="pred-kicker">Primary category</div>
            <div class="pred-badge">
                <span class="tag">{html.escape(label)}</span>
                {review_tag}
            </div>
            <div class="pred-conf">
                <span class="pct">{conf_pct:.1f}%</span>
                <span class="hint">model confidence</span>
            </div>
            <div class="pred-bar"><span style="width:{min(100.0, conf_pct):.1f}%"></span></div>
            {alts_html}
            <div class="pred-model">Model · {model}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_live_classify() -> None:
    samples = {
        "Billing error": "I was charged twice for the same subscription invoice.",
        "Late delivery": "My package is still in transit and the ETA keeps slipping.",
        "Account locked": "I cannot reset my password and the OTP never arrives.",
        "App crash": "The mobile app freezes right after the latest update.",
    }

    # Apply sample text BEFORE the text_area widget is created (Streamlit rule).
    pending = st.session_state.pop("live_sample_pending", None)
    if pending is not None:
        st.session_state.live_classify_text = pending
        st.session_state.pop("live_prediction", None)

    st.caption("Predictions show model confidence, not absolute certainty.")
    left, right = st.columns([1.1, 1], gap="large")
    run = False

    with left:
        st.text_area(
            "Complaint text",
            height=140,
            placeholder="Describe the issue…",
            key="live_classify_text",
            label_visibility="visible",
        )
        st.markdown(
            '<p class="live-sample-label">Try a sample</p>',
            unsafe_allow_html=True,
        )
        sample_row, classify_row = st.columns([4.2, 1], gap="small")
        with sample_row:
            picked = st.pills(
                "Samples",
                options=list(samples.keys()),
                selection_mode="single",
                key="live_sample_pills",
                label_visibility="collapsed",
            )
            if picked and st.session_state.get("live_sample_applied") != picked:
                st.session_state.live_sample_pending = samples[picked]
                st.session_state.live_sample_applied = picked
                st.rerun()
        with classify_row:
            st.markdown('<div style="height:0.15rem"></div>', unsafe_allow_html=True)
            run = st.button("Classify", type="primary", use_container_width=True)

    text = str(st.session_state.get("live_classify_text", "")).strip()

    with right:
        st.markdown(
            '<p class="live-field-label">Prediction</p>',
            unsafe_allow_html=True,
        )
        if run:
            if not text:
                st.session_state.live_prediction = None
                st.warning("Enter complaint text or pick a sample first.")
            else:
                with st.spinner("Classifying…"):
                    try:
                        pred = api_post("/predict", json={"text": text})
                    except requests.RequestException as exc:
                        st.session_state.live_prediction = None
                        st.error(f"Classification request failed: {exc}")
                        pred = None
                if pred is not None:
                    if pred.status_code == 200:
                        st.session_state.live_prediction = pred.json()
                    else:
                        st.session_state.live_prediction = None
                        st.error(friendly_http_error("Classification failed", pred))

        result = st.session_state.get("live_prediction")
        if result:
            render_prediction_card(result)
        else:
            st.markdown(
                """
                <div class="skeleton-card">
                    <div class="skel-label"></div>
                    <div class="skel-title"></div>
                    <div class="skel-bar"><span></span></div>
                    <div class="skel-meta">Predicted category and confidence will appear here.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# --- App ---
inject_styles()
init_state()

st.markdown(
    """
    <div class="hero">
        <p class="brand">Insight<span>AI</span></p>
        <p class="tagline">Complaint intelligence - classify, review, and track resolution SLAs.</p>
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
    status_cls = "" if ok else " down"
    status_label = "Online" if ok else "Offline"
    brand_col, refresh_col = st.columns([4, 1])
    with brand_col:
        st.markdown(
            f"""
            <div class="sidebar-header">
                <p class="sidebar-brand">InsightAI</p>
                <span class="status-dot{status_cls}"><i></i>{status_label}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Complaint intelligence")
    with refresh_col:
        if st.button("↻", help="Refresh dashboard data", key="sidebar_refresh"):
            with st.spinner("Refreshing…"):
                load_dashboard_data()
            st.rerun()

    st.session_state.section = st.radio(
        "Navigation",
        options=SECTIONS,
        index=SECTIONS.index(st.session_state.section)
        if st.session_state.section in SECTIONS
        else 0,
        label_visibility="collapsed",
    )

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Data</div>', unsafe_allow_html=True)
    if SAMPLE_CSV_PATH.is_file():
        st.download_button(
            "Download sample CSV",
            data=SAMPLE_CSV_PATH.read_bytes(),
            file_name="insightai_sample_upload.csv",
            mime="text/csv",
            use_container_width=True,
            help="48 held-out demo complaints. Upload this file to run the demo.",
            key="dl_sample_csv",
        )
    if FEATURE_GUIDE_PATH.is_file():
        st.download_button(
            "Feature guide (PDF)",
            data=FEATURE_GUIDE_PATH.read_bytes(),
            file_name="InsightAI_Feature_Guide.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="dl_feature_guide",
        )
    uploaded_file = st.file_uploader(
        "Upload CSV",
        type=["csv"],
        label_visibility="collapsed",
        help="Upload a complaint CSV to classify.",
    )
    if uploaded_file is not None:
        if st.button("Ingest data", type="primary", use_container_width=True):
            with st.spinner("Uploading and starting classification…"):
                try:
                    res = api_post(
                        "/upload",
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                "text/csv",
                            )
                        },
                    )
                except requests.RequestException as exc:
                    st.error(f"Upload failed: {exc}")
                else:
                    if res.status_code in (200, 202):
                        payload = res.json()
                        st.session_state.active_job_id = payload.get("job_id")
                        if payload.get("deduplicated"):
                            st.info("Identical file already processed - opened existing job.")
                        else:
                            st.success("Ingestion started")
                        st.rerun()
                    else:
                        st.error(friendly_http_error("Upload failed", res))

    render_job_panel()

    with st.expander("Settings", expanded=False):
        st.session_state.api_key = st.text_input(
            "API key",
            value=st.session_state.api_key,
            type="password",
            help="Only needed when AUTH_ENABLED=true on the API.",
            placeholder="Optional",
        )

    version = os.getenv("APP_VERSION", "2.1.0")
    model_tag = st.session_state.model_version or "model pending"
    st.markdown(
        f'<div class="sidebar-footer">v{version} · {model_tag}</div>',
        unsafe_allow_html=True,
    )

if not st.session_state.bootstrapped and ok and not polling:
    with st.spinner("Loading dashboard…"):
        load_dashboard_data()
    st.session_state.bootstrapped = True

if st.session_state.last_error:
    st.error(st.session_state.last_error)

if not ok and st.session_state.analytics_data is None:
    empty_state(
        "Backend unavailable",
        "Start the API (`uvicorn backend.main:app --reload`), then tap ↻ in the sidebar.",
    )
    st.stop()

data = st.session_state.analytics_data
if data is None:
    empty_state(
        "No analytics loaded",
        "Upload `data/sample_upload.csv` from the sidebar, or tap ↻ to reload.",
    )
    st.stop()

if st.session_state.loading:
    st.info("Loading…")

section = st.session_state.section
if section != "Complaint Explorer":
    st.markdown(f"### {section}")

if section == "Overview":
    render_overview(data)
elif section == "Review Queue":
    render_review_queue(data)
elif section == "Complaint Explorer":
    render_explorer(data)
else:
    render_live_classify()
