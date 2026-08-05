"""Đóng gói output/ thành output.zip để nộp bài, đồng thời lưu 1 bản có đánh
version + timestamp vào submissions/ để theo dõi lịch sử các lần nộp (tránh
tình trạng không rõ zip hiện tại ứng với lần chạy pipeline nào).

Chạy: uv run python scripts/package_output.py
"""

import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
SUBMIT_ZIP = ROOT / "output.zip"
SUBMISSIONS_DIR = ROOT / "submissions"
EXPECTED_COUNT = 50


def _next_version() -> int:
    existing = list(SUBMISSIONS_DIR.glob("output_v*.zip"))
    if not existing:
        return 1
    versions = []
    for f in existing:
        try:
            versions.append(int(f.stem.split("_v")[1].split("_")[0]))
        except (IndexError, ValueError):
            continue
    return max(versions, default=0) + 1


def _write_zip(zip_path: Path, files: list[Path]) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=f"output/{f.name}")


def main() -> int:
    files = sorted(OUTPUT_DIR.glob("EC_*.json"))
    if len(files) != EXPECTED_COUNT:
        print(
            f"CẢNH BÁO: output/ có {len(files)} file EC_*.json, kỳ vọng đúng {EXPECTED_COUNT}. "
            f"Kiểm tra lại trước khi nộp.",
            file=sys.stderr,
        )

    SUBMISSIONS_DIR.mkdir(exist_ok=True)
    version = _next_version()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    versioned_path = SUBMISSIONS_DIR / f"output_v{version}_{timestamp}.zip"

    _write_zip(versioned_path, files)
    _write_zip(SUBMIT_ZIP, files)

    print(f"Đã tạo {SUBMIT_ZIP.name} ({len(files)} file) — bản để nộp.")
    print(f"Đã lưu bản lưu vết: submissions/{versioned_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
