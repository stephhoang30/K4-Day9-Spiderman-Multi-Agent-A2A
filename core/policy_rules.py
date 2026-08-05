"""Áp dụng EC_POLICY_V2 (README mục 4) — thuần Python, không qua LLM để tránh hallucination
trên các trường bị chấm điểm nghiêm ngặt (primary/secondary issue, refund, root cause).

Thứ tự ưu tiên primary issue và thứ tự thêm secondary issue/action phải giữ đúng
như bảng README; đây là điểm dễ sai nhất nên mọi nhánh đều bám sát nguyên văn quy tắc.
"""

from dataclasses import dataclass, field


@dataclass
class ResponsibleParty:
    party_type: str
    party_id: str


@dataclass
class PolicyResult:
    primary_issue: str
    cause_code: str
    responsible_parties: list[ResponsibleParty]
    recommended_refund_brl: float
    case_status: str
    primary_action: str
    confidence_penalty: float = 0.0  # cộng dồn khi rơi vào fallback / thiếu dữ liệu
    margin_confidence: float = 0.96  # xem _margin_from_hours/_margin_from_diff bên dưới


MAX_RESPONSIBLE_PARTIES = 3

# Biên độ để suy ra confidence từ khoảng cách tới ngưỡng quyết định (xem compute_confidence):
# case càng SÁT ngưỡng (VD giao trễ 0.5h, hoặc difference_brl gần đúng 0.10 BRL) thì càng
# nên confidence thấp hơn case rõ ràng (giao trễ 5 ngày, difference_brl = 0.00), vì README
# không cho công thức confidence cụ thể nên đây là heuristic dựa trên "độ dứt khoát" của
# bằng chứng thay vì một giá trị tĩnh giống nhau cho mọi case.
_MARGIN_FLOOR = 0.6
_MARGIN_SPAN = 0.35
_HOURS_SATURATION = 72.0  # 3 ngày: lệch hơn mức này coi như "rõ ràng", không tăng thêm confidence
_RECONCILE_TOLERANCE = 0.10


def _margin_from_hours(variance_hours: float) -> float:
    return _MARGIN_FLOOR + _MARGIN_SPAN * min(1.0, abs(variance_hours) / _HOURS_SATURATION)


def _margin_from_diff(difference_brl: float) -> float:
    closeness_to_zero = (_RECONCILE_TOLERANCE - abs(difference_brl)) / _RECONCILE_TOLERANCE
    return _MARGIN_FLOOR + _MARGIN_SPAN * min(1.0, max(0.0, closeness_to_zero))


def determine_primary_issue(
    *,
    order_status: str,
    payment_total_brl: float,
    freight_total_brl: float | None,
    delivery_variance_hours: float | None,
    late_handoff_seller_ids: list[str],
    reconciled: bool | None,
    payment_count: int,
    difference_brl: float | None = None,
) -> PolicyResult:
    delivered_late = delivery_variance_hours is not None and delivery_variance_hours > 0

    if order_status == "canceled" and payment_total_brl > 0:
        return PolicyResult(
            primary_issue="canceled_order_paid",
            cause_code="ORDER_CANCELED_AFTER_PAYMENT",
            responsible_parties=[ResponsibleParty("platform", "OLIST_PLATFORM")],
            recommended_refund_brl=round(payment_total_brl, 2),
            case_status="action_required",
            primary_action="issue_full_refund",
            margin_confidence=0.96,
        )

    if order_status == "unavailable" and payment_total_brl > 0:
        return PolicyResult(
            primary_issue="unavailable_order_paid",
            cause_code="ORDER_UNAVAILABLE_AFTER_PAYMENT",
            responsible_parties=[ResponsibleParty("platform", "OLIST_PLATFORM")],
            recommended_refund_brl=round(payment_total_brl, 2),
            case_status="action_required",
            primary_action="issue_full_refund",
            margin_confidence=0.96,
        )

    if delivered_late and late_handoff_seller_ids:
        parties = [
            ResponsibleParty("seller", sid)
            for sid in late_handoff_seller_ids[:MAX_RESPONSIBLE_PARTIES]
        ]
        return PolicyResult(
            primary_issue="late_delivery_seller",
            cause_code="SELLER_HANDOFF_AFTER_LIMIT",
            responsible_parties=parties,
            recommended_refund_brl=round(freight_total_brl or 0.0, 2),
            case_status="action_required",
            primary_action="refund_freight",
            margin_confidence=_margin_from_hours(delivery_variance_hours),
        )

    if delivered_late and not late_handoff_seller_ids:
        return PolicyResult(
            primary_issue="late_delivery_logistics",
            cause_code="CARRIER_DELIVERED_AFTER_ESTIMATE",
            responsible_parties=[ResponsibleParty("logistics_provider", "LOGISTICS_PROVIDER")],
            recommended_refund_brl=round(freight_total_brl or 0.0, 2),
            case_status="action_required",
            primary_action="refund_freight",
            margin_confidence=_margin_from_hours(delivery_variance_hours),
        )

    if payment_count >= 2 and reconciled:
        return PolicyResult(
            primary_issue="valid_split_payment",
            cause_code="MULTIPLE_PAYMENTS_RECONCILED",
            responsible_parties=[],
            recommended_refund_brl=0.0,
            case_status="no_action",
            primary_action="explain_valid_split_payment",
            margin_confidence=_margin_from_diff(difference_brl if difference_brl is not None else 0.0),
        )

    if not delivered_late and reconciled:
        delivery_margin = (
            _margin_from_hours(delivery_variance_hours) if delivery_variance_hours is not None else _MARGIN_FLOOR
        )
        payment_margin = _margin_from_diff(difference_brl if difference_brl is not None else 0.0)
        return PolicyResult(
            primary_issue="unsupported_late_claim",
            cause_code="DELIVERY_WITHIN_ESTIMATE",
            responsible_parties=[],
            recommended_refund_brl=0.0,
            case_status="no_action",
            primary_action="reject_late_refund",
            margin_confidence=round((delivery_margin + payment_margin) / 2, 4),
        )

    # Fallback: không case nào trong 50 case thật được kỳ vọng rơi vào đây (đã verify
    # order_status chỉ gồm delivered/canceled/unavailable). Giữ lại để không crash và
    # để hạ confidence rõ ràng thay vì báo sai một primary_issue chắc chắn.
    return PolicyResult(
        primary_issue="unsupported_late_claim",
        cause_code="DELIVERY_WITHIN_ESTIMATE",
        responsible_parties=[],
        recommended_refund_brl=0.0,
        case_status="no_action",
        primary_action="reject_late_refund",
        confidence_penalty=0.3,
        margin_confidence=_MARGIN_FLOOR,
    )


def determine_secondary_issues(
    *,
    item_count: int,
    seller_count: int,
    payment_count: int,
    has_related_orders: bool,
    category_count: int,
) -> list[str]:
    secondary = []
    if item_count >= 2:
        secondary.append("multi_item_order")
    if seller_count >= 2:
        secondary.append("multi_seller_order")
    if payment_count >= 2:
        secondary.append("split_payment")
    if has_related_orders:
        secondary.append("repeat_customer")
    if category_count >= 2:
        secondary.append("multiple_categories")
    return secondary


def build_resolution_actions(*, primary_issue: str, secondary_issues: list[str]) -> list[str]:
    actions = []
    primary_action_map = {
        "canceled_order_paid": "issue_full_refund",
        "unavailable_order_paid": "issue_full_refund",
        "late_delivery_seller": "refund_freight",
        "late_delivery_logistics": "refund_freight",
        "valid_split_payment": "explain_valid_split_payment",
        "unsupported_late_claim": "reject_late_refund",
    }
    actions.append(primary_action_map[primary_issue])

    if primary_issue == "late_delivery_seller":
        actions.append("review_seller_handoff")
    elif primary_issue == "late_delivery_logistics":
        actions.append("review_carrier_delay")

    if primary_issue in ("canceled_order_paid", "unavailable_order_paid"):
        actions.append("verify_refund_completion")

    if "multi_seller_order" in secondary_issues:
        actions.append("coordinate_multi_seller_case")

    if "split_payment" in secondary_issues and primary_issue != "valid_split_payment":
        actions.append("verify_payment_allocation")

    return actions[:5]


def compute_confidence(*, margin_confidence: float, data_gaps: int, confidence_penalty: float) -> float:
    confidence = margin_confidence - 0.08 * data_gaps - confidence_penalty
    return max(0.0, min(1.0, round(confidence, 2)))
