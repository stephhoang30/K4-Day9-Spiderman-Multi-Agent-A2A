"""Validation read-only: quet moi file trong output/, chay 12 luat kiem, in tong so loi.

Khong sua file nao. Dung: python scripts/validate_output.py
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.verifier import verify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "output")


def main(argv):
    paths = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.json")))
    if not paths:
        print("0 file, 0 lỗi")
        return 0

    total_errors = 0
    for path in paths:
        case_id = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, encoding="utf-8") as fh:
                result = json.load(fh)
        except json.JSONDecodeError as exc:
            print(f"{os.path.basename(path)}: không parse được JSON: {exc}")
            total_errors += 1
            continue

        errors = verify(result, expected_case_id=case_id)
        total_errors += len(errors)
        for err in errors:
            print(f"{os.path.basename(path)}: {err}")

    print(f"{len(paths)} file, {total_errors} lỗi")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
