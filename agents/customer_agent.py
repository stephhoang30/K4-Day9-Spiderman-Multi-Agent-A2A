"""Customer Agent: xác định customer_unique_id + lịch sử order liên quan.

Chạy song song với Order & Product Agent nên tự lấy order row, không chờ agent kia.
"""

from core.customer import analyze_customer
from core.data_loader import get_store
from llm.llm_client import narrate


def run(state: dict) -> dict:
    case_id = state["case_input"]["case_id"]
    order_id = state["order_id"]
    store = get_store()

    order = store.get_order(order_id)
    result = analyze_customer(store, order_id, order)

    note = narrate(
        system_prompt=(
            "Bạn là Customer Agent trong hệ thống điều tra khiếu nại e-commerce. "
            "Chỉ diễn giải ngắn gọn (tối đa 2 câu) đúng dữ liệu được cung cấp, "
            "không suy đoán hay bịa thêm sự kiện không có trong dữ liệu."
        ),
        user_prompt=(
            f"customer_unique_id={result['customer_unique_id']}; "
            f"số order khác của cùng khách hàng={len(result['related_order_ids'])}."
        ),
    )

    return {
        "customer_result": result,
        "trace": [
            {
                "case_id": case_id,
                "agent": "customer_agent",
                "input_summary": {"order_id": order_id},
                "output_summary": {
                    "customer_unique_id": result["customer_unique_id"],
                    "related_order_count": len(result["related_order_ids"]),
                },
                "note": note,
            }
        ],
    }
