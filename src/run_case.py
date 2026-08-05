"""Chay mot case: doc file input, chay het chuoi agent, in ra JSON ket qua.

Dung: python -m src.run_case tests/fixtures/EC_SAMPLE.json
"""
from __future__ import annotations

import json
import sys

from src import bus
from src.agents import coordinator_agent
from src.datastore import get_case_bundle


def run_case(case: dict) -> dict:
    """Tra ve {result, errors}. Khong ghi file o day."""
    order_id = case["customer_request"]["claimed_order_id"]
    return coordinator_agent(case, get_case_bundle(order_id))


def _main(argv):
    if len(argv) < 2:
        print("dung: python -m src.run_case <duong_dan_input.json>")
        return 1

    with open(argv[1], encoding="utf-8") as fh:
        case = json.load(fh)

    bus.reset_trace()
    outcome = run_case(case)

    print(json.dumps(outcome["result"], ensure_ascii=False, indent=2))
    if outcome["errors"]:
        print("\nVERIFIER BAO LOI:", file=sys.stderr)
        for err in outcome["errors"]:
            print(" -", err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
