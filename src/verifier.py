"""12 luat kiem, rut tu README.md muc 3, 4, 5 va 6.

verify() tra ve list loi; rong nghia la dat. Day la bo kiem xac dinh — model
khong duoc phep lat ket luan cua no.

Cho nao chan that: `scripts/make_zip.py` khong dong goi khi con loi, va ca
run_all.py lan run_case.py deu tra exit code khac 0. run_all.py VAN ghi file
xuong output/ du con loi — thieu han mot file la case do chac chan 0 diem,
con file sai mot truong thi cac truong con lai van an diem.
"""
from __future__ import annotations

import re

from src.datastore import load_all

TOP_LEVEL_KEYS = [
    "case_id",
    "case_assessment",
    "affected_entities",
    "customer_context",
    "product_context",
    "delivery_analysis",
    "payment_reconciliation",
    "root_cause_analysis",
    "evidence_ids",
    "financial_resolution",
    "resolution_actions",
]

LIMITS = {
    ("affected_entities", "order_ids"): 5,
    ("affected_entities", "item_ids"): 5,
    ("affected_entities", "seller_ids"): 3,
    ("affected_entities", "payment_ids"): 5,
    ("customer_context", "related_order_ids"): 5,
    ("product_context", "product_ids"): 5,
    ("product_context", "category_names"): 5,
}

TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
EVIDENCE_RE = re.compile(
    r"^(order:[0-9a-f]{32}"
    r"|item:[0-9a-f]{32}:\d+"
    r"|payment:[0-9a-f]{32}:\d+"
    r"|seller:[0-9a-f]{32}"
    r"|policy:[A-Z_]+)$"
)

VALID_STATUS = {"action_required", "no_action"}
VALID_CAUSES = {
    "SELLER_HANDOFF_AFTER_LIMIT",
    "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT",
    "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED",
    "DELIVERY_WITHIN_ESTIMATE",
}


def _check_timestamp(errors, label, value):
    if value is None:
        return
    if not isinstance(value, str) or not TIMESTAMP_RE.match(value):
        errors.append(f"luat 9: {label} sai dang YYYY-MM-DD HH:MM:SS: {value!r}")


def verify(result: dict, expected_case_id: str | None = None) -> list[str]:
    errors: list[str] = []

    # Luat 1 — du khoa cap mot, khong thua khoa la
    missing = [k for k in TOP_LEVEL_KEYS if k not in result]
    extra = [k for k in result if k not in TOP_LEVEL_KEYS]
    if missing:
        errors.append(f"luat 1: thieu khoa cap mot {missing}")
    if extra:
        errors.append(f"luat 1: thua khoa la {extra}")
    if missing:
        return errors  # thieu khoa thi cac luat sau khong con cho de kiem

    assessment = result["case_assessment"]
    entities = result["affected_entities"]
    delivery = result["delivery_analysis"]
    payment = result["payment_reconciliation"]
    refund = result["financial_resolution"]["recommended_refund_brl"]

    # Luat 2 — case_id khop ten file input
    if expected_case_id and result["case_id"] != expected_case_id:
        errors.append(f"luat 2: case_id {result['case_id']!r} khac {expected_case_id!r}")

    # Luat 3 — confidence trong doan 0 den 1
    confidence = assessment.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append(f"luat 3: confidence ngoai doan [0,1]: {confidence!r}")

    # Luat 4 — case_status hop le
    if assessment.get("case_status") not in VALID_STATUS:
        errors.append(f"luat 4: case_status khong hop le: {assessment.get('case_status')!r}")

    # Luat 5 va 6 — gioi han mang
    for (section, field), limit in LIMITS.items():
        values = result[section].get(field, [])
        if len(values) > limit:
            errors.append(f"luat 5-6: {section}.{field} co {len(values)} phan tu, toi da {limit}")
    if len(result["evidence_ids"]) > 20:
        errors.append(f"luat 5-6: evidence_ids co {len(result['evidence_ids'])} phan tu, toi da 20")
    if len(result["resolution_actions"]) > 5:
        errors.append("luat 5-6: resolution_actions qua 5 phan tu")
    causes = result["root_cause_analysis"]["ranked_causes"]
    parties = result["root_cause_analysis"]["responsible_parties"]
    if len(causes) > 3:
        errors.append("luat 5-6: ranked_causes qua 3 phan tu")
    if len(parties) > 3:
        errors.append("luat 5-6: responsible_parties qua 3 phan tu")

    # Luat 7 — moi evidence_id khop 1 trong 5 dang
    for evidence_id in result["evidence_ids"]:
        if not EVIDENCE_RE.match(str(evidence_id)):
            errors.append(f"luat 7: evidence_id sai dang: {evidence_id!r}")
    for cause in causes:
        if cause.get("cause_code") not in VALID_CAUSES:
            errors.append(f"luat 7: cause_code khong co trong bang: {cause.get('cause_code')!r}")

    # Luat 8 — moi ID trong evidence ton tai that trong CSV
    idx = load_all()
    for evidence_id in result["evidence_ids"]:
        kind, _, rest = str(evidence_id).partition(":")
        if kind == "order" and rest not in idx["orders"]:
            errors.append(f"luat 8: order khong co trong CSV: {rest}")
        elif kind == "seller" and rest not in idx["sellers"]:
            errors.append(f"luat 8: seller khong co trong CSV: {rest}")
        elif kind == "item":
            order_id, _, item_no = rest.partition(":")
            rows = idx["items"].get(order_id, [])
            if item_no not in [r["order_item_id"] for r in rows]:
                errors.append(f"luat 8: item khong co trong CSV: {evidence_id}")
        elif kind == "payment":
            order_id, _, seq = rest.partition(":")
            rows = idx["payments"].get(order_id, [])
            if seq not in [r["payment_sequential"] for r in rows]:
                errors.append(f"luat 8: payment khong co trong CSV: {evidence_id}")

    # Luat 9 — timestamp giu nguyen dang trong CSV hoac null
    _check_timestamp(errors, "delivered_at", delivery.get("delivered_at"))
    _check_timestamp(errors, "estimated_delivery_at", delivery.get("estimated_delivery_at"))
    _check_timestamp(errors, "carrier_handoff_at", delivery.get("carrier_handoff_at"))
    for row in delivery.get("seller_handoff_analysis", []):
        _check_timestamp(errors, "shipping_limit_at", row.get("shipping_limit_at"))

    # Luat 10 — order khong co item row thi 3 truong tien la null, cac mang rong
    if not entities["item_ids"]:
        for field in ("expected_total_brl", "difference_brl", "reconciled"):
            if payment.get(field) is not None:
                errors.append(f"luat 10: khong co item row nhung {field} khong phai null")
        for section, field in (
            ("affected_entities", "seller_ids"),
            ("product_context", "product_ids"),
            ("product_context", "category_names"),
        ):
            if result[section].get(field):
                errors.append(f"luat 10: khong co item row nhung {section}.{field} khong rong")
        if delivery.get("seller_handoff_analysis"):
            errors.append("luat 10: khong co item row nhung seller_handoff_analysis khong rong")

    # Luat 11 — case_status va refund phai khop nhau
    if assessment.get("case_status") == "action_required" and not (refund > 0):
        errors.append(f"luat 11: action_required nhung refund = {refund}")
    if assessment.get("case_status") == "no_action" and refund != 0:
        errors.append(f"luat 11: no_action nhung refund = {refund}")

    # Luat 12 — order lich su khong duoc nam trong affected_entities
    overlap = set(result["customer_context"]["related_order_ids"]) & set(entities["order_ids"])
    if overlap:
        errors.append(f"luat 12: order lich su lot vao affected_entities: {sorted(overlap)}")

    return errors
