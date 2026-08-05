"""Tính delivery variance và seller handoff variance theo đúng công thức README mục 4;
timestamp không hợp lệ (NaN/rỗng) được coi là None thay vì crash khi parse.
"""

from core.utils import dedup_preserve_order, hours_between, is_valid_timestamp


def analyze_delivery(order: dict, items: list[dict]) -> dict:
    delivered_at = order["order_delivered_customer_date"]
    delivered_at = delivered_at if is_valid_timestamp(delivered_at) else None

    estimated_at = order["order_estimated_delivery_date"]
    estimated_at = estimated_at if is_valid_timestamp(estimated_at) else None

    carrier_at = order["order_delivered_carrier_date"]
    carrier_at = carrier_at if is_valid_timestamp(carrier_at) else None

    delivery_variance_hours = (
        hours_between(estimated_at, delivered_at)
        if estimated_at is not None and delivered_at is not None
        else None
    )

    seller_ids = dedup_preserve_order([it["seller_id"] for it in items])
    seller_handoff_analysis = []
    for seller_id in seller_ids:
        limits = [it["shipping_limit_date"] for it in items if it["seller_id"] == seller_id]
        shipping_limit_at = min(limits)
        handoff_variance_hours = (
            hours_between(shipping_limit_at, carrier_at) if carrier_at is not None else None
        )
        late_handoff = handoff_variance_hours is not None and handoff_variance_hours > 0
        seller_handoff_analysis.append(
            {
                "seller_id": seller_id,
                "shipping_limit_at": shipping_limit_at,
                "handoff_variance_hours": handoff_variance_hours,
                "late_handoff": late_handoff,
            }
        )

    late_handoff_seller_ids = [
        s["seller_id"] for s in seller_handoff_analysis if s["late_handoff"]
    ]

    return {
        "delivered_at": delivered_at,
        "estimated_delivery_at": estimated_at,
        "carrier_handoff_at": carrier_at,
        "delivery_variance_hours": delivery_variance_hours,
        "seller_handoff_analysis": seller_handoff_analysis,
        "late_handoff_seller_ids": late_handoff_seller_ids,
    }
