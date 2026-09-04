"""Generate docs/InsightAI_Feature_Guide.pdf (stdlib only)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "InsightAI_Feature_Guide.pdf"

PAGES: list[list[tuple[str, int]]] = [
    [
        ("InsightAI Feature Guide", 20),
        ("Complaint intelligence for classify, review, and SLA tracking.", 11),
        ("Version 2.1 - demo walkthrough for operators and stakeholders.", 11),
        ("", 11),
        ("1. What InsightAI does", 13),
        ("Upload a CSV of complaint texts. The model classifies each row into", 11),
        ("Billing, Shipping, Service, or Technical, scores confidence, and flags", 11),
        ("low-confidence rows for human review. Analytics track volume, mix,", 11),
        ("resolution SLAs, and system alerts.", 11),
        ("", 11),
        ("2. Quick demo path", 13),
        ("- Download sample CSV from the sidebar (48 held-out complaints).", 11),
        ("- Click Upload, select the file, then Ingest data.", 11),
        ("- Wait for the job to complete, then open Overview.", 11),
        ("- Triage Needs Review items, then explore filters and Live Classify.", 11),
    ],
    [
        ("3. Overview", 13),
        ("KPI cards: total complaints, resolved under 24h, needs-review count,", 11),
        ("and median resolution time. Semantic colors (red/amber) appear only for", 11),
        ("risk states on Needs Review - not decoration.", 11),
        ("", 11),
        ("System alerts highlight actionable anomalies (review overload, weak", 11),
        ("class confidence, SLA risk).", 11),
        ("", 11),
        ("Charts: colored category bars plus a donut mix so volume share is", 11),
        ("obvious at a glance. Recent ingestion jobs sit beside the charts with", 11),
        ("export and retry when a run fails.", 11),
        ("", 11),
        ("If Needs Review is above zero, use Triage pending reviews to jump", 11),
        ("straight into the Review Queue.", 11),
    ],
    [
        ("4. Review Queue", 13),
        ("Lists low-confidence complaints, lowest confidence first. Click a row", 11),
        ("to open Triage. The dropdown defaults to the model suggestion so you", 11),
        ("can Approve / Submit in one click when the label is correct, or change", 11),
        ("the category when it is not.", 11),
        ("", 11),
        ("Each submit clears needs_review and marks the row human_reviewed so", 11),
        ("Overview can show how many labels you corrected for future retraining.", 11),
        ("", 11),
        ("When the queue is empty, return to Overview for refreshed KPIs.", 11),
        ("", 11),
        ("5. Complaint Explorer", 13),
        ("Search and filter by category, review status, and sort. Export CSV uses", 11),
        ("the active filters. Pagination sits under the table.", 11),
    ],
    [
        ("6. Live Classification", 13),
        ("Paste any complaint (or pick a sample chip) and Classify. The result", 11),
        ("card shows the primary category badge, confidence percent with a bar,", 11),
        ("and runner-up alternatives so you can see model uncertainty live.", 11),
        ("", 11),
        ("7. Sidebar", 13),
        ("- Status dot: API online/offline.", 11),
        ("- Download sample CSV: safe demo file (not the training set).", 11),
        ("- Feature guide PDF: this document.", 11),
        ("- Upload + Ingest: start a classification job.", 11),
        ("- Settings: optional API key when AUTH_ENABLED=true.", 11),
        ("- Footer: app version and loaded model tag.", 11),
        ("", 11),
        ("8. Data notes", 13),
        ("sample_upload.csv is held-out demo text. complaints.csv is for training", 11),
        ("only (python -m ml.train). Do not upload the training file as a demo.", 11),
    ],
]


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _content_stream(lines: list[tuple[str, int]]) -> bytes:
    y = 750.0
    parts: list[str] = ["BT", "/F1 11 Tf", "50 750 Td"]
    first = True
    for text, size in lines:
        if not first:
            # move down relative
            parts.append(f"0 -{18 if size >= 13 else 14} Td")
        first = False
        parts.append(f"/F1 {size} Tf")
        if text:
            parts.append(f"({_escape(text)}) Tj")
        else:
            parts.append("() Tj")
        y -= 18 if size >= 13 else 14
    parts.append("ET")
    raw = "\n".join(parts).encode("latin-1", errors="replace")
    return b"<< /Length %d >>\nstream\n" % len(raw) + raw + b"\nendstream"


def build_pdf() -> bytes:
    # Objects: 1=Catalog, 2=Pages, 3=Font, then page/content pairs
    objs: list[bytes] = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    # placeholder for pages - fill after we know kids
    objs.append(b"")  # index 1 -> obj 2
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_refs: list[str] = []
    for lines in PAGES:
        page_id = len(objs) + 1  # next object number
        content_id = page_id + 1
        page_refs.append(f"{page_id} 0 R")
        objs.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Contents {content_id} 0 R "
                f"/Resources << /Font << /F1 3 0 R >> >> >>"
            ).encode("latin-1")
        )
        objs.append(_content_stream(lines))

    objs[1] = (
        f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>"
    ).encode("latin-1")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode("latin-1"))
        out.extend(body)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objs) + 1}\n".encode("latin-1"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
    out.extend(
        f"trailer<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode(
            "latin-1"
        )
    )
    return bytes(out)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = build_pdf()
    OUT.write_bytes(data)
    print(f"Wrote {OUT} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
