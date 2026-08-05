"""Payment Agent: đối soát payment vs item + freight — thuần tính toán, không LLM
vì độ chính xác số liệu quan trọng hơn narration (xem architecture.md)."""

from core.data_loader import get_store
from core.payment import analyze_payment


def run(state: dict) -> dict:
    case_id = state["case_input"]["case_id"]
    order_id = state["order_id"]
    store = get_store()

    items = state["order_product_result"]["items"]
    payments = store.get_payments(order_id)

    result = analyze_payment(items, payments)
    result["payment_count"] = len(payments)

    return {
        "payment_result": result,
        "trace": [
            {
                "case_id": case_id,
                "agent": "payment_agent",
                "input_summary": {"item_count": len(items), "payment_count": len(payments)},
                "output_summary": {
                    "expected_total_brl": result["expected_total_brl"],
                    "payment_total_brl": result["payment_total_brl"],
                    "reconciled": result["reconciled"],
                },
            }
        ],
    }
