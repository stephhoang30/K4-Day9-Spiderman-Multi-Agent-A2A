"""Nhận diện customer_unique_id và lịch sử order khác của cùng khách hàng.

Order đã lấy sẵn ở coordinator để tránh gọi get_order 2 lần cho cùng order_id.
"""


def analyze_customer(store, order_id: str, order: dict) -> dict:
    customer_id = order["customer_id"]
    customer = store.get_customer(customer_id)
    customer_unique_id = customer["customer_unique_id"] if customer else None

    related_order_ids = (
        store.get_related_order_ids(customer_unique_id, order_id)
        if customer_unique_id
        else []
    )

    return {
        "customer_id": customer_id,
        "customer_unique_id": customer_unique_id,
        "related_order_ids": related_order_ids,
    }
