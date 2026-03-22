import streamlit as st
import requests
import pandas as pd

st.title("📊 InsightAI Dashboard")

BASE_URL = "http://127.0.0.1:8000"

# Upload CSV
uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    files = {"file": uploaded_file.getvalue()}
    res = requests.post(
     f"{BASE_URL}/upload",
     files={"file": ("file.csv", uploaded_file.getvalue())}
    )

    if res.status_code == 200:
        st.success("File uploaded successfully")

# Analytics
if st.button("Refresh Analytics"):
    res = requests.get(f"{BASE_URL}/analytics/summary")

    if res.status_code == 200:
        data = res.json()

        st.metric("Total Complaints", data["total_complaints"])
        st.metric("Resolved < 24h (%)", round(data["north_star_metric"], 2))

        st.subheader("Category Distribution")
        st.write(data["category_distribution"])

        st.subheader("Top Issues")
        st.write(data["top_issues"])