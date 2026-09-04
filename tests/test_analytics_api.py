def _seed(client, monkeypatch, rows: list[tuple[str, str, str, str]], confidence: float = 0.9):
    monkeypatch.setattr(
        "backend.services.ingestion.predict",
        lambda text: (
            {"category": "technical", "confidence": 0.9}
            if text == "health check probe"
            else {"category": "billing", "confidence": confidence}
        ),
    )
    lines = ["text,created_at,resolved_at"]
    for text, created, resolved, _cat in rows:
        lines.append(f'"{text}",{created},{resolved}')
    csv_content = "\n".join(lines) + "\n"
    response = client.post(
        "/api/v1/upload",
        files={"file": ("seed.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 202


def test_complaints_search_and_pagination(client, monkeypatch):
    _seed(
        client,
        monkeypatch,
        [
            ("Alpha billing issue", "2026-01-01 09:00:00", "2026-01-01 12:00:00", "billing"),
            ("Beta shipping delay", "2026-01-02 09:00:00", "2026-01-03 09:00:00", "billing"),
            ("Gamma billing refund", "2026-01-03 09:00:00", "2026-01-03 10:00:00", "billing"),
        ],
    )

    page1 = client.get("/api/v1/complaints", params={"page": 1, "page_size": 2}).json()
    assert page1["total"] == 3
    assert page1["total_pages"] == 2
    assert len(page1["items"]) == 2

    search = client.get("/api/v1/complaints", params={"search": "shipping"}).json()
    assert search["total"] == 1
    assert "shipping" in search["items"][0]["text"].lower()


def test_complaints_sort_and_needs_review_filter(client, monkeypatch):
    def fake_predict(text):
        if text == "health check probe":
            return {"category": "technical", "confidence": 0.9}
        if "uncertain" in text:
            return {"category": "billing", "confidence": 0.2}
        return {"category": "service", "confidence": 0.95}

    monkeypatch.setattr("backend.services.ingestion.predict", fake_predict)
    csv_content = (
        "text,created_at,resolved_at\n"
        '"uncertain charge",2026-01-01 09:00:00,2026-01-01 10:00:00\n'
        '"clear service complaint",2026-01-02 09:00:00,2026-01-02 11:00:00\n'
    )
    client.post(
        "/api/v1/upload",
        files={"file": ("mix.csv", csv_content, "text/csv")},
    )

    review = client.get("/api/v1/complaints", params={"needs_review": True}).json()
    assert review["total"] == 1
    assert review["items"][0]["needs_review"] is True
    assert review["items"][0]["category"] == "billing"

    sorted_asc = client.get(
        "/api/v1/complaints",
        params={"sort_by": "confidence", "sort_order": "asc"},
    ).json()
    confidences = [row["confidence"] for row in sorted_asc["items"]]
    assert confidences == sorted(confidences)


def test_complaints_rejects_bad_sort(client):
    response = client.get("/api/v1/complaints", params={"sort_by": "password"})
    assert response.status_code == 400


def test_analytics_insights_empty_and_populated(client, monkeypatch):
    empty = client.get("/api/v1/analytics/summary").json()
    assert empty["total_complaints"] == 0
    assert empty["insights"]
    assert empty["insights"][0]["code"] == "insufficient_data"
    assert empty["unresolved_count"] == 0

    _seed(
        client,
        monkeypatch,
        [
            ("Invoice wrong amount", "2026-01-01 09:00:00", "2026-01-01 12:00:00", "billing"),
            ("Invoice missing tax", "2026-01-02 09:00:00", "2026-01-04 09:00:00", "billing"),
            ("Invoice duplicate fee", "2026-01-03 09:00:00", "2026-01-03 15:00:00", "billing"),
            ("Invoice currency error", "2026-01-04 09:00:00", "2026-01-04 20:00:00", "billing"),
            ("Invoice seat mismatch", "2026-01-05 09:00:00", "2026-01-05 18:00:00", "billing"),
        ],
        confidence=0.9,
    )
    summary = client.get("/api/v1/analytics/summary").json()
    assert summary["total_complaints"] == 5
    assert summary["resolved_count"] == 5
    assert summary["avg_resolution_hours"] is not None
    assert summary["median_resolution_hours"] is not None
    assert summary["within_24h_count"] >= 1
    # High-confidence seed → no review-overload insight restating KPIs
    assert not any(item["code"] == "review_rate" for item in summary["insights"])


def test_analytics_resolution_sql_aggregates(client, monkeypatch):
    """Resolution avg/median/SLA come from SQL aggregates (not Python datetime loops)."""
    _seed(
        client,
        monkeypatch,
        [
            ("R1", "2026-01-01 00:00:00", "2026-01-01 06:00:00", "billing"),  # 6h
            ("R2", "2026-01-01 00:00:00", "2026-01-01 12:00:00", "billing"),  # 12h
            ("R3", "2026-01-01 00:00:00", "2026-01-02 12:00:00", "billing"),  # 36h
        ],
        confidence=0.9,
    )
    summary = client.get("/api/v1/analytics/summary").json()
    assert summary["resolved_count"] == 3
    assert summary["avg_resolution_hours"] == 18.0
    assert summary["median_resolution_hours"] == 12.0
    assert summary["within_24h_count"] == 2
    assert summary["north_star_metric"] == round((2 / 3) * 100, 2)
