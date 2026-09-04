"""Reset local SQLite DB + uploads so demos start clean."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "insight.db"
UPLOADS = ROOT / "data" / "uploads"


def main() -> int:
    if DB.exists():
        try:
            DB.unlink()
            print(f"Removed {DB}")
        except PermissionError:
            print(
                f"Could not delete {DB} — stop the API (uvicorn) first, then rerun:\n"
                f"  python scripts/reset_local_db.py"
            )
            return 1
    else:
        print(f"No DB at {DB}")

    if UPLOADS.exists():
        shutil.rmtree(UPLOADS)
        print(f"Removed {UPLOADS}")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    print(f"Ready uploads dir: {UPLOADS}")
    print("Restart API, then upload data/sample_upload.csv (not complaints.csv).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
