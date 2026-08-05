"""Tổng hợp item, seller và category của order; item rỗng nghĩa là mọi mảng đều rỗng
theo đúng README mục 4, không suy diễn thêm dữ liệu sản phẩm.
"""

from core.utils import dedup_preserve_order


def analyze_order_product(store, order_id: str) -> dict:
    items = store.get_items(order_id)

    seller_ids = dedup_preserve_order([it["seller_id"] for it in items])
    product_ids = dedup_preserve_order([it["product_id"] for it in items])

    # Dùng nguyên category_name gốc (tiếng Bồ) từ products.csv, KHÔNG dịch sang
    # tiếng Anh: field output tên "category_names" khớp trực tiếp tên cột CSV
    # "product_category_name", không phải "product_category_name_english";
    # README không có chỗ nào yêu cầu dịch.
    category_names_en = []
    for pid in product_ids:
        product = store.get_product(pid)
        if product is None:
            continue
        category_name = product["product_category_name"]
        if not isinstance(category_name, str):
            continue
        category_names_en.append(category_name)
    category_names_en = dedup_preserve_order(category_names_en)

    return {
        "items": items,
        "seller_ids": seller_ids,
        "product_ids": product_ids,
        "category_names_en": category_names_en,
    }
