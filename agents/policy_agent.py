"""Policy Agent: áp EC_POLICY_V2 lên kết quả 4 agent trước đó (không tự đọc CSV).

Quyết định primary/secondary issue, refund, action đều qua core/policy_rules.py
(thuần code); LLM chỉ viết justification cho trace, không ảnh hưởng số liệu.
"""

from core.policy_rules import (
    build_resolution_actions,
    compute_confidence,
    determine_primary_issue,
    determine_secondary_issues,
)
from llm.llm_client import narrate


def run(state: dict) -> dict:
    case_id = state["case_input"]["case_id"]
    customer = state["customer_result"]
    op = state["order_product_result"]
    payment = state["payment_result"]
    delivery = state["delivery_result"]

    primary = determine_primary_issue(
        order_status=op["order_status"],
        payment_total_brl=payment["payment_total_brl"],
        freight_total_brl=payment["freight_total_brl"],
        delivery_variance_hours=delivery["delivery_variance_hours"],
        late_handoff_seller_ids=delivery["late_handoff_seller_ids"],
        reconciled=payment["reconciled"],
        payment_count=payment["payment_count"],
        difference_brl=payment["difference_brl"],
    )

    secondary = determine_secondary_issues(
        item_count=len(op["items"]),
        seller_count=len(op["seller_ids"]),
        payment_count=payment["payment_count"],
        has_related_orders=len(customer["related_order_ids"]) > 0,
        category_count=len(op["category_names_en"]),
    )

    actions = build_resolution_actions(primary_issue=primary.primary_issue, secondary_issues=secondary)

    data_gaps = sum(
        [
            len(op["items"]) == 0,
            payment["payment_count"] == 0,
            customer["customer_unique_id"] is None,
        ]
    )
    confidence = compute_confidence(
        margin_confidence=primary.margin_confidence,
        data_gaps=data_gaps,
        confidence_penalty=primary.confidence_penalty,
    )

    note = narrate(
        system_prompt=(
            "Bạn là Policy Agent, áp dụng EC_POLICY_V2 cho khiếu nại e-commerce. "
            "Viết justification ngắn gọn (tối đa 3 câu) giải thích TẠI SAO primary_issue "
            "và responsible party được chọn, chỉ dựa trên số liệu cung cấp, không bịa thêm."
        ),
        user_prompt=(
            f"primary_issue={primary.primary_issue}; cause_code={primary.cause_code}; "
            f"responsible_parties={[(p.party_type, p.party_id) for p in primary.responsible_parties]}; "
            f"recommended_refund_brl={primary.recommended_refund_brl}; secondary_issues={secondary}."
        ),
    )

    result = {
        "primary_issue": primary.primary_issue,
        "secondary_issues": secondary,
        "case_status": primary.case_status,
        "confidence": confidence,
        "cause_code": primary.cause_code,
        "responsible_parties": [
            {"party_type": p.party_type, "party_id": p.party_id} for p in primary.responsible_parties
        ],
        "recommended_refund_brl": primary.recommended_refund_brl,
        "resolution_actions": actions,
    }

    return {
        "policy_result": result,
        "trace": [
            {
                "case_id": case_id,
                "agent": "policy_agent",
                "input_summary": {
                    "order_status": op["order_status"],
                    "delivery_variance_hours": delivery["delivery_variance_hours"],
                    "reconciled": payment["reconciled"],
                },
                "output_summary": result,
                "note": note,
            }
        ],
    }
