import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# CONFIG
st.set_page_config(page_title="InsightAI", layout="wide")

BASE_URL = "http://127.0.0.1:8000"

# CUSTOM CSS
st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #1f2937, #111827);
    color: white;
}

.block-container {
    padding-top: 2rem;
}

.metric-card {
    background: rgba(255, 255, 255, 0.08);
    padding: 20px;
    border-radius: 16px;
    backdrop-filter: blur(10px);
    text-align: center;
}

.title {
    font-size: 40px;
    font-weight: 700;
}

.subtitle {
    color: #9ca3af;
}

.stButton>button {
    border-radius: 10px;
    padding: 10px 20px;
    background: linear-gradient(to right, #6366f1, #8b5cf6);
    color: white;
    border: none;
}

.stButton>button:hover {
    background: linear-gradient(to right, #4f46e5, #7c3aed);
}
</style>
""", unsafe_allow_html=True)


# HEADER
st.markdown('<div class="title">📊 InsightAI Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-powered complaint intelligence system</div>', unsafe_allow_html=True)

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

# ANALYTICS BUTTON
if st.button("🔄 Refresh Analytics"):

    with st.spinner("📊 Fetching insights..."):
        res = requests.get(f"{BASE_URL}/analytics/summary")

    if res.status_code != 200:
        st.error("❌ Backend not responding")
        st.stop()

    data = res.json()

    # KPI CARDS
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h2>📦 Total Complaints</h2>
            <h1>{data["total_complaints"]}</h1>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h2>⚡ Resolved &lt; 24h</h2>
            <h1>{data["north_star_metric"]}%</h1>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # CATEGORY CHART
    st.subheader("📈 Category Distribution")

    cat_df = pd.DataFrame(
        list(data["category_distribution"].items()),
        columns=["Category", "Percentage"]
    )

    # Clean labels
    cat_df["Category"] = cat_df["Category"].replace({
        "needs_review": "Uncertain"
    })

    if not cat_df.empty:
        fig = px.bar(
            cat_df,
            x="Category",
            y="Percentage",
            color="Category",
            text_auto=True,
            template="plotly_dark"
        )

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # DRILL DOWN
    st.subheader("🔍 Drill Down Analysis")

    if not cat_df.empty:
        selected_category = st.selectbox(
            "Select Category",
            cat_df["Category"]
        )

        # Map back to original value
        reverse_map = {"Uncertain": "needs_review"}
        selected_category_db = reverse_map.get(selected_category, selected_category)

        res2 = requests.get(f"{BASE_URL}/complaints")

        if res2.status_code == 200:
            df = pd.DataFrame(res2.json())

            filtered = df[df["category"] == selected_category_db]

            if not filtered.empty:
                filtered["confidence"] = (filtered["confidence"] * 100).round(1)

                st.dataframe(
                    filtered.style.background_gradient(
                        subset=["confidence"], cmap="Blues"
                    ),
                    use_container_width=True
                )
            else:
                st.info("No complaints in this category")

    st.divider()

    # TOP ISSUES
    st.subheader("🔥 Top Issues")

    for category, count in data["top_issues"]:
        st.markdown(f"👉 **{category}** — {count} complaints")

    st.divider()

    # RECENT DATA
    st.subheader("📋 Recent Complaints")

    res2 = requests.get(f"{BASE_URL}/complaints")

    if res2.status_code == 200:
        df = pd.DataFrame(res2.json())
        st.dataframe(df, use_container_width=True)