"""Đối soát tổng payment với item + freight; order không có item row thì không có
cơ sở đối soát nên expected/difference/reconciled phải null (README mục 4).
"""

from core.utils import dedup_preserve_order, round2


def analyze_payment(items: list[dict], payments: list[dict]) -> dict:
    item_total_brl = round2(sum(it["price"] for it in items))
    freight_total_brl = round2(sum(it["freight_value"] for it in items))
    payment_total_brl = round2(sum(p["payment_value"] for p in payments))

    if len(items) == 0:
        expected_total_brl = None
        difference_brl = None
        reconciled = None
    else:
        expected_total_brl = round2(item_total_brl + freight_total_brl)
        difference_brl = round2(payment_total_brl - expected_total_brl)
        reconciled = abs(difference_brl) <= 0.10

    payment_types = dedup_preserve_order([p["payment_type"] for p in payments])

    return {
        "item_total_brl": item_total_brl,
        "freight_total_brl": freight_total_brl,
        "payment_total_brl": payment_total_brl,
        "expected_total_brl": expected_total_brl,
        "difference_brl": difference_brl,
        "reconciled": reconciled,
        "payment_types": payment_types,
    }
