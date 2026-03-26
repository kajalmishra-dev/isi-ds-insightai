import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# CONFIG
st.set_page_config(page_title="InsightAI", layout="wide")

BASE_URL = "http://127.0.0.1:8000"

# Initialize session state
if "analytics_data" not in st.session_state:
    st.session_state.analytics_data = None
if "complaints_data" not in st.session_state:
    st.session_state.complaints_data = None

# HEADER
st.title("📊 InsightAI Dashboard")
st.caption("AI-powered complaint intelligence system")

st.divider()

# SIDEBAR
st.sidebar.title("⚙️ Controls")

uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    with st.spinner("🚀 Processing..."):
        res = requests.post(
            f"{BASE_URL}/upload",
            files={"file": ("file.csv", uploaded_file.getvalue())}
        )

    if res.status_code == 200:
        st.sidebar.success("✅ Upload successful")
    else:
        st.sidebar.error("❌ Upload failed")

# BUTTON - Store data in session state
if st.button("🔄 Refresh Analytics"):

    # FETCH ANALYTICS
    with st.spinner("📊 Fetching insights..."):
        res = requests.get(f"{BASE_URL}/analytics/summary")

    if res.status_code != 200:
        st.error("❌ Backend not responding")
    else:
        st.session_state.analytics_data = res.json()
        
        # Fetch complaints data too
        res_complaints = requests.get(f"{BASE_URL}/complaints")
        if res_complaints.status_code == 200:
            st.session_state.complaints_data = pd.DataFrame(res_complaints.json())

# DISPLAY ANALYTICS (outside button block so it persists)
if st.session_state.analytics_data is not None:
    
    data = st.session_state.analytics_data

    # KPI CARDS
    col1, col2 = st.columns(2)

    col1.metric("📦 Total Complaints", data["total_complaints"])
    col2.metric("⚡ Resolved < 24h (%)", data["north_star_metric"])

    st.divider()

    # CATEGORY DISTRIBUTION
    st.subheader("📈 Category Distribution")

    cat_df = pd.DataFrame(
        list(data["category_distribution"].items()),
        columns=["Category", "Percentage"]
    )

    # Rename label
    cat_df["Category"] = cat_df["Category"].replace({
        "needs_review": "Uncertain"
    })

    if not cat_df.empty:
        fig = px.bar(
            cat_df,
            x="Category",
            y="Percentage",
            color="Category",
            text_auto=True
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # 🔍 DRILL DOWN ANALYSIS
    st.subheader("🔍 Drill Down Analysis")

    if not cat_df.empty and st.session_state.complaints_data is not None:

        selected_categories = st.multiselect(
            "Select Categories",
            cat_df["Category"],
            default=cat_df["Category"].tolist()
        )

        # ✅ FIXED: Handle empty selection gracefully
        if not selected_categories:
            st.info("ℹ️ Please select at least one category to view complaints")
        else:
            # Map UI → DB values
            reverse_map = {"Uncertain": "needs_review"}

            selected_categories_db = [
                reverse_map.get(cat, cat) for cat in selected_categories
            ]

            # Use data from session state
            df = st.session_state.complaints_data
            filtered = df[df["category"].isin(selected_categories_db)].copy()

            if not filtered.empty:
                filtered.loc[:, "confidence"] = (filtered["confidence"] * 100).round(1)
                st.dataframe(filtered, use_container_width=True)
            else:
                st.info("No complaints in selected categories")

    st.divider()

    # 🔥 TOP ISSUES
    st.subheader("🔥 Top Issues")

    for item in data["top_issues"]:
        st.markdown(f"👉 **{item['category']}** — {item['count']} complaints")

    st.divider()

    # 📋 RECENT DATA
    st.subheader("📋 Recent Complaints")

    if st.session_state.complaints_data is not None:
        st.dataframe(st.session_state.complaints_data, use_container_width=True)
    else:
        st.info("Click 'Refresh Analytics' to load data")