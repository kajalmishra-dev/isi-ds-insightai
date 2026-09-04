"""Generate a more visual docs/InsightAI_Feature_Guide.pdf (stdlib only)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "InsightAI_Feature_Guide.pdf"

# RGB 0-1 for PDF
BLUE = (0.0, 0.443, 0.890)  # #0071e3
INK = (0.114, 0.114, 0.122)  # #1d1d1f
MUTED = (0.431, 0.431, 0.451)  # #6e6e73
LINE = (0.91, 0.91, 0.93)
WHITE = (1.0, 1.0, 1.0)
SOFT = (0.945, 0.965, 1.0)  # light blue wash
GREEN = (0.204, 0.780, 0.349)
ORANGE = (1.0, 0.624, 0.039)
PURPLE = (0.686, 0.322, 0.871)
RED = (1.0, 0.231, 0.188)


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _rgb(rgb: tuple[float, float, float]) -> str:
    return f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f}"


def _rect(x: float, y: float, w: float, h: float, fill: tuple[float, float, float] | None = None,
          stroke: tuple[float, float, float] | None = None, width: float = 1.0) -> str:
    parts = []
    if fill:
        parts.append(f"{_rgb(fill)} rg")
    if stroke:
        parts.append(f"{width:.2f} w {_rgb(stroke)} RG")
    parts.append(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re")
    if fill and stroke:
        parts.append("B")
    elif fill:
        parts.append("f")
    else:
        parts.append("S")
    return " ".join(parts)


def _text(x: float, y: float, text: str, size: float = 11, color: tuple[float, float, float] = INK,
          bold: bool = False) -> str:
    font = "/F2" if bold else "/F1"
    return (
        f"BT {font} {size:.1f} Tf {_rgb(color)} rg {x:.1f} {y:.1f} Td ({_esc(text)}) Tj ET"
    )


def _wrap(text: str, max_chars: int = 78) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = (" ".join(cur + [w]))
        if len(trial) <= max_chars:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines or [""]


class PageBuilder:
    def __init__(self) -> None:
        self.ops: list[str] = []
        self.y = 720.0

    def add(self, op: str) -> None:
        self.ops.append(op)

    def header(self, title: str, subtitle: str | None = None) -> None:
        self.add(_rect(0, 742, 612, 50, fill=BLUE))
        self.add(_text(40, 762, title, size=18, color=WHITE, bold=True))
        if subtitle:
            self.add(_text(40, 748, subtitle, size=9, color=WHITE))
        self.add(_rect(40, 730, 80, 3, fill=ORANGE))
        self.y = 705

    def footer(self, page: int, total: int) -> None:
        self.add(_rect(40, 36, 532, 0.6, fill=LINE))
        self.add(_text(40, 22, "InsightAI  ·  Feature Guide  ·  v2.1", size=8, color=MUTED))
        self.add(_text(520, 22, f"{page}/{total}", size=8, color=MUTED))

    def h2(self, text: str) -> None:
        self.y -= 8
        self.add(_rect(40, self.y - 4, 6, 16, fill=BLUE))
        self.add(_text(54, self.y, text, size=13, color=INK, bold=True))
        self.y -= 22

    def para(self, text: str, size: float = 10.5) -> None:
        for line in _wrap(text, 82):
            self.add(_text(40, self.y, line, size=size, color=INK))
            self.y -= 14
        self.y -= 4

    def bullet(self, text: str) -> None:
        self.add(_rect(46, self.y + 2, 4, 4, fill=BLUE))
        for i, line in enumerate(_wrap(text, 78)):
            self.add(_text(58, self.y, line, size=10.5, color=INK))
            self.y -= 14
        self.y -= 2

    def callout(self, title: str, body: str, fill: tuple[float, float, float] = SOFT) -> None:
        lines = _wrap(body, 74)
        h = 28 + len(lines) * 13
        self.y -= 4
        box_y = self.y - h + 16
        self.add(_rect(40, box_y, 532, h, fill=fill, stroke=LINE, width=0.8))
        self.add(_rect(40, box_y, 5, h, fill=BLUE))
        self.add(_text(56, self.y, title, size=10, color=BLUE, bold=True))
        self.y -= 14
        for line in lines:
            self.add(_text(56, self.y, line, size=10, color=INK))
            self.y -= 13
        self.y = box_y - 12

    def chips(self, items: list[tuple[str, tuple[float, float, float]]]) -> None:
        x = 40.0
        self.y -= 2
        for label, color in items:
            w = 8 + len(label) * 6.2
            self.add(_rect(x, self.y - 2, w, 18, fill=color))
            self.add(_text(x + 8, self.y + 2, label, size=9, color=WHITE, bold=True))
            x += w + 10
        self.y -= 28

    def step_row(self, num: str, title: str, detail: str) -> None:
        self.add(_rect(40, self.y - 6, 22, 22, fill=BLUE))
        self.add(_text(46.5, self.y, num, size=11, color=WHITE, bold=True))
        self.add(_text(72, self.y + 2, title, size=11, color=INK, bold=True))
        self.y -= 14
        for line in _wrap(detail, 76):
            self.add(_text(72, self.y, line, size=10, color=MUTED))
            self.y -= 13
        self.y -= 8

    def build(self) -> bytes:
        raw = "\n".join(self.ops).encode("latin-1", errors="replace")
        return b"<< /Length %d >>\nstream\n" % len(raw) + raw + b"\nendstream"


def page_cover() -> bytes:
    b = PageBuilder()
    b.add(_rect(0, 0, 612, 792, fill=BLUE))
    b.add(_rect(0, 0, 612, 220, fill=INK))
    b.add(_text(48, 620, "InsightAI", size=36, color=WHITE, bold=True))
    b.add(_text(48, 590, "Feature Guide", size=22, color=WHITE))
    b.add(_rect(48, 568, 64, 4, fill=ORANGE))
    b.add(_text(48, 540, "Complaint intelligence for classify, review,", size=12, color=WHITE))
    b.add(_text(48, 522, "and resolution SLA tracking.", size=12, color=WHITE))
    b.add(_text(48, 160, "Demo walkthrough  ·  v2.1  ·  FastAPI + Streamlit + ML", size=10, color=WHITE))
    b.add(_text(48, 140, "Billing  ·  Shipping  ·  Service  ·  Technical", size=10, color=(0.8, 0.85, 1.0)))
    b.add(_text(48, 40, "Download sample CSV from the sidebar to run the guided demo.", size=9, color=(0.75, 0.8, 0.95)))
    return b.build()


def page_tour() -> bytes:
    b = PageBuilder()
    b.header("Product tour", "What each screen is for")
    b.h2("Categories the model predicts")
    b.chips(
        [
            ("Billing", BLUE),
            ("Shipping", GREEN),
            ("Service", ORANGE),
            ("Technical", PURPLE),
        ]
    )
    b.para(
        "Low-confidence predictions are flagged Needs Review (red semantic state) so humans can approve or reclassify before analytics treat them as final."
    )
    b.h2("4-step demo path")
    b.step_row("1", "Download sample CSV", "Use the sidebar button - 48 held-out demo complaints, not the training file.")
    b.step_row("2", "Upload + Ingest", "Start an async job. Watch progress, then open Overview when it completes.")
    b.step_row("3", "Triage the queue", "Jump from Needs Review into Review Queue. Approve or fix labels in one click.")
    b.step_row("4", "Explore + Live Classify", "Filter the corpus, export CSV, then try sample chips in Live Classification.")
    b.callout(
        "Tip",
        "Do not upload data/complaints.csv for demos. That file is for python -m ml.train only.",
    )
    b.footer(2, 4)
    return b.build()


def page_screens() -> bytes:
    b = PageBuilder()
    b.header("Screens", "Overview · Review · Explorer · Live")
    b.h2("Overview")
    b.bullet("KPI strip: volume, SLA under 24h, needs-review load, median resolution.")
    b.bullet("Colored category bars + donut mix for share-of-volume.")
    b.bullet("System alerts for review overload, weak classes, and SLA risk.")
    b.bullet("Triage N pending reviews routes you straight into the Review Queue.")
    b.h2("Review Queue")
    b.bullet("Lowest confidence first. Row selection highlights the triage card.")
    b.bullet("Dropdown defaults to the model suggestion - Approve / Submit in one click.")
    b.bullet("Human reviews mark feedback for future retraining.")
    b.h2("Complaint Explorer")
    b.bullet("Labeled filters: Category, Review, Sort - plus search and filtered export.")
    b.bullet("Compact timestamps; job IDs stay out of the main grid.")
    b.h2("Live Classification")
    b.bullet("Paste text or try a sample chip, then Classify.")
    b.bullet("Result card: category badge, confidence bar, and runner-up alternatives.")
    b.footer(3, 4)
    return b.build()


def page_sidebar() -> bytes:
    b = PageBuilder()
    b.header("Sidebar & data", "Ops controls for demos and deploys")
    b.h2("Sidebar controls")
    b.bullet("Online / Offline status dot + refresh.")
    b.bullet("Download sample CSV - safe demo file.")
    b.bullet("Feature guide PDF - this document.")
    b.bullet("Upload + Ingest - start classification jobs.")
    b.bullet("Settings - optional API key when AUTH_ENABLED=true.")
    b.bullet("Footer - app version and loaded model tag.")
    b.h2("Files that matter")
    b.callout(
        "data/sample_upload.csv",
        "Held-out demo texts (zero overlap with training). Download from UI or copy from the repo.",
    )
    b.callout(
        "data/complaints.csv",
        "Labeled training set for ml.train only. Not for demo uploads.",
    )
    b.callout(
        "docs/InsightAI_Feature_Guide.pdf",
        "This guide. Regenerate with: python scripts/generate_feature_guide_pdf.py",
        fill=(1.0, 0.97, 0.92),
    )
    b.para(
        "InsightAI is built for a circular workflow: Overview signals risk, Review clears it, Explorer audits the corpus, Live Classify validates the model on new wording.",
        size=10,
    )
    b.footer(4, 4)
    return b.build()


def build_pdf() -> bytes:
    pages = [page_cover(), page_tour(), page_screens(), page_sidebar()]
    objs: list[bytes] = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"")  # pages placeholder
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    page_refs: list[str] = []
    for content in pages:
        page_id = len(objs) + 1
        content_id = page_id + 1
        page_refs.append(f"{page_id} 0 R")
        objs.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Contents {content_id} 0 R "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>"
            ).encode("latin-1")
        )
        objs.append(content)

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
