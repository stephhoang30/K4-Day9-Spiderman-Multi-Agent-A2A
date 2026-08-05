"""Chay het input/*.json, ghi output/<ten file input>, in tien do va tong loi.

Khong nuot exception: mot case loi phai hien ten ra, khong duoc bien mat trong im lang.
Dung: python src/run_all.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import bus
from src.datastore import load_all
from src.run_case import run_case

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(ROOT, "input")
OUTPUT_DIR = os.path.join(ROOT, "output")


def main(argv):
    paths = sorted(glob.glob(os.path.join(INPUT_DIR, "*.json")))
    if not paths:
        print(f"không tìm thấy file input nào trong {INPUT_DIR}")
        return 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    load_all()
    bus.reset_trace()

    started = time.perf_counter()
    done, failed, total_errors = 0, [], 0

    for path in paths:
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            case = json.load(fh)
        try:
            outcome = run_case(case)
        except Exception as exc:  # noqa: BLE001 - phai in ten case loi ra
            failed.append(f"{name}: {type(exc).__name__}: {exc}")
            continue

        errors = outcome["errors"]
        if errors:
            # Van ghi file: thieu file la case do chac chan 0 diem, con file sai mot
            # truong thi cac truong con lai van an diem. Cho chan that la make_zip.py.
            total_errors += len(errors)
            failed.append(f"{name}: {len(errors)} lỗi verifier — vẫn ghi file, make_zip.py sẽ chặn")
            for err in errors:
                print(f"  {name}: {err}")

        with open(os.path.join(OUTPUT_DIR, name), "w", encoding="utf-8") as fh:
            json.dump(outcome["result"], fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        done += 1
        print(f"[{done}/{len(paths)}] {name} -> {outcome['result']['case_assessment']['primary_issue']}")

    elapsed = time.perf_counter() - started
    print(f"\n{done} case xong trong {elapsed:.1f}s, {total_errors} lỗi verifier")
    for line in failed:
        print("FAIL", line)
    return 0 if (done == len(paths) and total_errors == 0) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
