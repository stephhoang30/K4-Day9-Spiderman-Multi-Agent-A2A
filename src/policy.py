"""EC_POLICY_V2 — chuoi dieu kien kiem theo thu tu co dinh, dung o nhanh khop dau tien.

Khong goi model. Cung mot bundle thi luon ra cung mot ket luan.
Thu tu uu tien va cong thuc: README.md muc 4 va muc 5.
"""
from __future__ import annotations

from src import variants

CAUSE_BY_PRIMARY = {
    "canceled_order_paid": "ORDER_CANCELED_AFTER_PAYMENT",
    "unavailable_order_paid": "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "late_delivery_seller": "SELLER_HANDOFF_AFTER_LIMIT",
    "late_delivery_logistics": "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "valid_split_payment": "MULTIPLE_PAYMENTS_RECONCILED",
    "unsupported_late_claim": "DELIVERY_WITHIN_ESTIMATE",
}

ACTION_BY_PRIMARY = {
    "canceled_order_paid": "issue_full_refund",
    "unavailable_order_paid": "issue_full_refund",
    "late_delivery_seller": "refund_freight",
    "late_delivery_logistics": "refund_freight",
    "valid_split_payment": "explain_valid_split_payment",
    "unsupported_late_claim": "reject_late_refund",
}

MAX_SELLER_IDS = 3
MAX_ITEM_IDS = 5
MAX_PAYMENT_IDS = 5
MAX_EVIDENCE = 20


def _pick_primary(order_status, paid_total, is_late, late_seller_ids, payment_rows, reconciled):
    """Kiem theo dung thu tu bang EC_POLICY_V2. Dung o nhanh dau tien khop."""
    if order_status == "canceled" and paid_total > 0:
        return "canceled_order_paid"
    if order_status == "unavailable" and paid_total > 0:
        return "unavailable_order_paid"
    if is_late and late_seller_ids:
        return "late_delivery_seller"
    if is_late:
        return "late_delivery_logistics"
    if payment_rows >= 2 and reconciled is True:
        return "valid_split_payment"
    # Con lai: khong co bang chung nao chong do yeu cau hoan tien.
    return "unsupported_late_claim"


def _secondary_issues(bundle, related_order_ids, category_names):
    """Them theo dung 5 thu tu o README.md muc 4, khong sap lai."""
    issues = []
    if len(bundle["items"]) >= 2:
        issues.append("multi_item_order")
    if len(bundle["sellers"]) >= 2:
        issues.append("multi_seller_order")
    if len(bundle["payments"]) >= 2:
        issues.append("split_payment")
    if related_order_ids:
        issues.append("repeat_customer")
    if len(category_names) >= 2:
        issues.append("multiple_categories")
    return issues


def _actions(primary, seller_count, payment_rows):
    """Action chinh truoc, roi action bo sung theo thu tu o README.md muc 4."""
    actions = [ACTION_BY_PRIMARY[primary]]
    if primary == "late_delivery_seller":
        actions.append("review_seller_handoff")
    elif primary == "late_delivery_logistics":
        actions.append("review_carrier_delay")
    if primary in ("canceled_order_paid", "unavailable_order_paid"):
        actions.append("verify_refund_completion")
    if seller_count >= 2:
        actions.append("coordinate_multi_seller_case")
    # Action chinh cua valid_split_payment da giai thich split payment roi.
    if payment_rows >= 2 and primary != "valid_split_payment":
        actions.append("verify_payment_allocation")
    return actions[:5]


def _evidence_ids(bundle, responsible_seller_ids, cause_codes):
    order_id = bundle["order_id"]
    evidence = [f"order:{order_id}"]
    for item in bundle["items"][:MAX_ITEM_IDS]:
        evidence.append(f"item:{order_id}:{item['order_item_id']}")
    for payment in bundle["payments"][:MAX_PAYMENT_IDS]:
        evidence.append(f"payment:{order_id}:{payment['payment_sequential']}")
    for seller_id in responsible_seller_ids:
        evidence.append(f"seller:{seller_id}")
    for cause_code in cause_codes:
        evidence.append(f"policy:{cause_code}")
    return evidence[:MAX_EVIDENCE]


def _ranked_causes(primary):
    """Mot cause cho moi primary issue, dung nhu vi du o README muc 6.

    Bien the SECOND_CAUSE phat them cause rank 2 cho nhanh late_delivery_seller:
    don do vua tre han giao vua tre ban giao, tuc thoa ca hai root cause.
    """
    codes = [CAUSE_BY_PRIMARY[primary]]
    if variants.SECOND_RANKED_CAUSE and primary == "late_delivery_seller":
        codes.append("CARRIER_DELIVERED_AFTER_ESTIMATE")
    return codes[:3]


def _confidence(bundle, delivery, payment, primary):
    """Xac dinh theo do day du cua du lieu, khong phai so do model doan."""
    score = 0.95 if bundle["order"] else 0.30
    if not bundle["items"]:
        score -= 0.05
    if payment["reconciled"] is False:
        score -= 0.10
    if primary in ("late_delivery_seller", "late_delivery_logistics"):
        if delivery["carrier_handoff_at"] is None:
            score -= 0.10
    if primary == "unsupported_late_claim" and not bundle["payments"]:
        score -= 0.10
    if variants.CONFIDENCE_ALWAYS_ONE:
        return 1.0
    return round(min(max(score, 0.0), 1.0), 2)


def classify(bundle: dict, analysis: dict) -> dict:
    """bundle tu src/datastore.py, analysis la dict gop ket qua 4 ham o src/tools.py.

    Tra ve: case_assessment, root_cause_analysis, financial_resolution,
            resolution_actions, evidence_ids.
    """
    order = bundle["order"] or {}
    delivery = analysis["delivery"]
    payment = analysis["payment"]
    customer = analysis["customer"]
    product = analysis["product"]

    variance = delivery["delivery_variance_hours"]
    is_late = variance is not None and variance > 0
    late_seller_ids = delivery["late_handoff_seller_ids"]

    primary = _pick_primary(
        order.get("order_status"),
        payment["payment_total_brl"],
        is_late,
        late_seller_ids,
        len(bundle["payments"]),
        payment["reconciled"],
    )

    if primary in ("canceled_order_paid", "unavailable_order_paid"):
        refund = payment["payment_total_brl"]
        parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
        responsible_sellers = []
    elif primary == "late_delivery_seller":
        refund = payment["freight_total_brl"]
        responsible_sellers = late_seller_ids[:MAX_SELLER_IDS]
        parties = [{"party_type": "seller", "party_id": s} for s in responsible_sellers]
    elif primary == "late_delivery_logistics":
        refund = payment["freight_total_brl"]
        parties = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
        responsible_sellers = []
    else:
        refund = 0.0
        parties = []
        responsible_sellers = []

    refund = round(refund, 2) + 0.0  # chuan hoa -0.0 -> 0.0 nhu src/tools._money
    cause_codes = _ranked_causes(primary)

    return {
        "case_assessment": {
            "primary_issue": primary,
            "secondary_issues": _secondary_issues(
                bundle, customer["related_order_ids"], product["category_names"]
            ),
            "case_status": "action_required" if refund > 0 else "no_action",
            "confidence": _confidence(bundle, delivery, payment, primary),
        },
        "root_cause_analysis": {
            "ranked_causes": [
                {"cause_code": code, "rank": i} for i, code in enumerate(cause_codes, 1)
            ],
            "responsible_parties": parties[:3],
        },
        "financial_resolution": {
            "currency": "BRL",
            "recommended_refund_brl": refund,
        },
        "resolution_actions": _actions(
            primary, len(bundle["sellers"]), len(bundle["payments"])
        ),
        "evidence_ids": _evidence_ids(bundle, responsible_sellers, cause_codes),
    }
