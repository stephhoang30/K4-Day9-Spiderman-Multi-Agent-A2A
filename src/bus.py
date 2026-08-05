"""A2A bus. Moi lan chuyen viec di qua day, va bus ghi mot dong trace.

Khong agent nao goi thang agent khac: quyen truy cap du lieu chi co y nghia
khi duong chuyen viec la duy nhat va kiem duoc.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE_PATH = os.path.join(ROOT, "logging", "trace.jsonl")


def reset_trace(path: str = TRACE_PATH) -> None:
    """Ghi de dau moi luot chay: README.md muc 8 yeu cau trace cua luot moi nhat."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8"):
        pass


def _write(line: dict, path: str = TRACE_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")


def envelope(sender: str, receiver: str, task: str, payload: dict) -> dict:
    return {"from": sender, "to": receiver, "task": task, "payload": payload}


def send(case_id: str, env: dict, handler) -> dict:
    """Goi handler(payload), do thoi gian, ghi trace, tra ket qua.

    Handler nem exception thi trace ghi status=error va exception duoc nem tiep:
    nuot loi o day se lam mot case bien mat trong im lang.
    """
    started = time.perf_counter()
    status, result = "ok", None
    try:
        result = handler(env["payload"])
        return result
    except Exception as exc:  # noqa: BLE001 - ghi trace roi nem tiep
        status = f"error:{type(exc).__name__}"
        raise
    finally:
        _write(
            {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "case_id": case_id,
                "from": env["from"],
                "to": env["to"],
                "task": env["task"],
                "payload_keys": sorted(env["payload"].keys()),
                "status": status,
                "result_keys": sorted(result.keys()) if isinstance(result, dict) else [],
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
        )


def note(case_id: str, sender: str, task: str, detail: dict) -> None:
    """Ghi mot dong trace khong gan voi lan chuyen viec nao (vi du: ket luan cua model)."""
    _write(
        {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "case_id": case_id,
            "from": sender,
            "to": "trace",
            "task": task,
            "payload_keys": sorted(detail.keys()),
            "status": "note",
            "detail": detail,
            "latency_ms": 0,
        }
    )
