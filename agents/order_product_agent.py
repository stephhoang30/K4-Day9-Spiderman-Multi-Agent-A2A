"""Order & Product Agent: trích item, seller, product, category của order.

Bổ sung `order_status` vào kết quả (ngoài phạm vi core/order_product.py) vì
Policy Agent cần trường này mà không được tự truy CSV (least-privilege).
"""

from core.data_loader import get_store
from core.order_product import analyze_order_product
from llm.llm_client import narrate


def run(state: dict) -> dict:
    case_id = state["case_input"]["case_id"]
    order_id = state["order_id"]
    store = get_store()

    result = analyze_order_product(store, order_id)
    order = store.get_order(order_id)
    result["order_status"] = order["order_status"] if order else None

    note = narrate(
        system_prompt=(
            "Bạn là Order & Product Agent. Chỉ tóm tắt ngắn gọn (tối đa 2 câu) "
            "số lượng item/seller/category được cung cấp, không suy đoán thêm."
        ),
        user_prompt=(
            f"order_status={result['order_status']}; số item={len(result['items'])}; "
            f"số seller={len(result['seller_ids'])}; category={result['category_names_en']}."
        ),
    )

    return {
        "order_product_result": result,
        "trace": [
            {
                "case_id": case_id,
                "agent": "order_product_agent",
                "input_summary": {"order_id": order_id},
                "output_summary": {
                    "order_status": result["order_status"],
                    "item_count": len(result["items"]),
                    "seller_count": len(result["seller_ids"]),
                },
                "note": note,
            }
        ],
    }
