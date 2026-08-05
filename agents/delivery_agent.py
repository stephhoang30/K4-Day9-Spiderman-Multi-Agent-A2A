"""Delivery Agent: tính delivery variance + seller handoff variance — thuần tính toán,
không LLM (cùng lý do với Payment Agent)."""

from core.data_loader import get_store
from core.delivery import analyze_delivery


def run(state: dict) -> dict:
    case_id = state["case_input"]["case_id"]
    order_id = state["order_id"]
    store = get_store()

    order = store.get_order(order_id)
    items = state["order_product_result"]["items"]

    result = analyze_delivery(order, items)

    return {
        "delivery_result": result,
        "trace": [
            {
                "case_id": case_id,
                "agent": "delivery_agent",
                "input_summary": {"item_count": len(items)},
                "output_summary": {
                    "delivery_variance_hours": result["delivery_variance_hours"],
                    "late_handoff_seller_ids": result["late_handoff_seller_ids"],
                },
            }
        ],
    }
