# Agent đơn hàng và sản phẩm

Truy xuất ngữ cảnh của đơn hàng, item, seller, sản phẩm và danh mục.

## Contract bàn giao

`OrderProductAgent(data_dir).investigate(order_id)` trả về:

- `order`: toàn bộ các trường gốc của order;
- `items`: item theo thứ tự trong CSV, kèm `item_id`, seller, giá, freight và category;
- `seller_ids`, `product_ids`, `category_names`: danh sách unique, giữ thứ tự xuất hiện.

Order không có item sẽ trả về các mảng rỗng. Agent không áp dụng policy, tính refund hay quyết định trách nhiệm.
