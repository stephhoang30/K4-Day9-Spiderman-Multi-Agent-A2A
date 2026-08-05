"""Tiện ích dùng chung: dedup giữ thứ tự, tính chênh lệch giờ giữa 2 timestamp CSV."""

from datetime import datetime

TS_FORMAT = "%Y-%m-%d %H:%M:%S"


def dedup_preserve_order(values: list) -> list:
    seen = set()
    out = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def is_valid_timestamp(value) -> bool:
    return isinstance(value, str) and value.strip() != "" and value.lower() != "nan"


def hours_between(start_ts: str, end_ts: str) -> float:
    """(end - start) tính bằng giờ, dương nghĩa là end xảy ra sau start."""
    start = datetime.strptime(start_ts, TS_FORMAT)
    end = datetime.strptime(end_ts, TS_FORMAT)
    return round((end - start).total_seconds() / 3600.0, 2)


def round2(value: float) -> float:
    return round(float(value), 2)
