# Agent đơn hàng và sản phẩm

Truy xuất ngữ cảnh của đơn hàng, item, seller, sản phẩm và danh mục.

## Contract bàn giao

`OrderProductAgent(data_dir).investigate(order_id)` chỉ trả các trường cần cho các agent sau:

- `order`: `order_id`, `customer_id`, `order_status`, ba timestamp giao hàng;
- `items`: item theo thứ tự trong CSV, gồm `item_id`, `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price`, `freight_value`, `category_name`;
- `seller_ids`, `product_ids`, `category_names`: danh sách unique, giữ thứ tự xuất hiện.

Order không có item sẽ trả về các mảng rỗng. Agent không áp dụng policy, tính refund hay quyết định trách nhiệm.
