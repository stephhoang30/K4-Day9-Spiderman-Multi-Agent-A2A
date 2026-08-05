"""Dong goi output.zip dung dinh dang bo cham yeu cau.

Entry trong zip phai la output/EC_001.json den output/EC_050.json — co tien to
thu muc, khong phai file phang, va khong lan file nao khac.

Script tu chay verifier truoc khi nen: khong dong goi mot bo output con loi.
Dung: python scripts/make_zip.py
"""
from __future__ import annotations

import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.verifier import verify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "output")
ZIP_PATH = os.path.join(ROOT, "output.zip")
MAX_BYTES = 5 * 1024 * 1024

EXPECTED = [f"EC_{i:03d}.json" for i in range(1, 51)]


def main(argv):
    missing = [n for n in EXPECTED if not os.path.exists(os.path.join(OUTPUT_DIR, n))]
    if missing:
        print(f"thiếu {len(missing)} file trong output/: {missing[:5]}")
        return 1

    total_errors = 0
    for name in EXPECTED:
        with open(os.path.join(OUTPUT_DIR, name), encoding="utf-8") as fh:
            result = json.load(fh)
        errors = verify(result, expected_case_id=os.path.splitext(name)[0])
        total_errors += len(errors)
        for err in errors:
            print(f"{name}: {err}")
    if total_errors:
        print(f"{total_errors} lỗi — không đóng gói")
        return 1

    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in EXPECTED:
            zf.write(os.path.join(OUTPUT_DIR, name), arcname=f"output/{name}")

    with zipfile.ZipFile(ZIP_PATH) as zf:
        entries = zf.namelist()
    size = os.path.getsize(ZIP_PATH)

    assert entries == [f"output/{n}" for n in EXPECTED], "entry trong zip sai thu tu hoac sai ten"
    print(f"output.zip: {len(entries)} entry, {size} bytes")
    print(f"entry đầu {entries[0]} | entry cuối {entries[-1]}")
    if size > MAX_BYTES:
        print(f"zip {size} bytes vượt trần 5 MB")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
