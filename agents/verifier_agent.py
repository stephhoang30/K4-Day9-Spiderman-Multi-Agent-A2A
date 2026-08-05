"""Verifier Agent: lắp ráp CaseOutput cuối cùng (áp giới hạn mảng + build evidence)
rồi validate bằng pydantic trước khi Coordinator ghi file.

Nếu validate lỗi: KHÔNG tự sửa số liệu, log lỗi rõ ràng vào trace và vẫn trả về
dict thô để Coordinator ghi đủ 50 file theo yêu cầu nộp bài, thay vì âm thầm bỏ qua.
"""

from pydantic import ValidationError

from core.data_loader import get_store
from core.evidence import build_evidence_ids
from core.schemas import CaseOutput


def assemble_case_output(state: dict) -> dict:
    case_id = state["case_input"]["case_id"]
    order_id = state["order_id"]
    customer = state["customer_result"]
    op = state["order_product_result"]
    payment = state["payment_result"]
    delivery = state["delivery_result"]
    policy = state["policy_result"]

    store = get_store()
    item_ids = [f"{order_id}:{it['order_item_id']}" for it in op["items"]]
    payments = store.get_payments(order_id)
    payment_ids = [f"{order_id}:{p['payment_sequential']}" for p in payments]

    affected_entities = {
        "order_ids": [order_id],
        "item_ids": item_ids[:5],
        "seller_ids": op["seller_ids"][:3],
        "payment_ids": payment_ids[:5],
    }

    responsible_seller_ids = [
        p["party_id"] for p in policy["responsible_parties"] if p["party_type"] == "seller"
    ][:3]

    evidence_ids = build_evidence_ids(
        order_id=order_id,
        item_ids=affected_entities["item_ids"],
        payment_ids=affected_entities["payment_ids"],
        responsible_seller_ids=responsible_seller_ids,
        cause_codes=[policy["cause_code"]],
    )

    return {
        "case_id": case_id,
        "case_assessment": {
            "primary_issue": policy["primary_issue"],
            "secondary_issues": policy["secondary_issues"][:5],
            "case_status": policy["case_status"],
            "confidence": policy["confidence"],
        },
        "affected_entities": affected_entities,
        "customer_context": {
            "customer_unique_id": customer["customer_unique_id"],
            "related_order_ids": customer["related_order_ids"][:5],
        },
        "product_context": {
            "product_ids": op["product_ids"][:5],
            "category_names": op["category_names_en"][:5],
        },
        "delivery_analysis": {
            "delivered_at": delivery["delivered_at"],
            "estimated_delivery_at": delivery["estimated_delivery_at"],
            "carrier_handoff_at": delivery["carrier_handoff_at"],
            "delivery_variance_hours": delivery["delivery_variance_hours"],
            "seller_handoff_analysis": delivery["seller_handoff_analysis"],
            "late_handoff_seller_ids": delivery["late_handoff_seller_ids"],
        },
        "payment_reconciliation": {
            "currency": "BRL",
            "item_total_brl": payment["item_total_brl"],
            "freight_total_brl": payment["freight_total_brl"],
            "expected_total_brl": payment["expected_total_brl"],
            "payment_total_brl": payment["payment_total_brl"],
            "difference_brl": payment["difference_brl"],
            "reconciled": payment["reconciled"],
            "payment_types": payment["payment_types"],
        },
        "root_cause_analysis": {
            "ranked_causes": [{"cause_code": policy["cause_code"], "rank": 1}],
            "responsible_parties": policy["responsible_parties"][:3],
        },
        "evidence_ids": evidence_ids,
        "financial_resolution": {
            "currency": "BRL",
            "recommended_refund_brl": policy["recommended_refund_brl"],
        },
        "resolution_actions": policy["resolution_actions"][:5],
    }


def run(state: dict) -> dict:
    case_id = state["case_input"]["case_id"]
    case_output = assemble_case_output(state)

    errors: list[dict] = []
    try:
        validated = CaseOutput(**case_output)
        case_output = validated.model_dump()
        valid = True
    except ValidationError as exc:
        valid = False
        errors = exc.errors()

    return {
        "verifier_result": {"case_output": case_output, "valid": valid, "errors": errors},
        "trace": [
            {
                "case_id": case_id,
                "agent": "verifier_agent",
                "valid": valid,
                "errors": errors,
            }
        ],
    }
