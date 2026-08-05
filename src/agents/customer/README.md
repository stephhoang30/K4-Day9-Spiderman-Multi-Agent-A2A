# Agent khách hàng

Xác định danh tính khách hàng và lịch sử các đơn hàng liên quan.

## Contract bàn giao

`CustomerAgent(data_dir).investigate(customer_id, claimed_order_id)` trả về:

- `customer_unique_id`: định danh khách xuyên nhiều order;
- `related_order_ids`: tối đa 5 order khác của cùng khách, theo thứ tự CSV;
- `related_order_count`: tổng số order liên quan trước khi giới hạn 5;
- `is_repeat_customer`: `true` nếu khách có ít nhất một order khác.

Agent xác nhận `claimed_order_id` thực sự thuộc `customer_id` trước khi bàn giao. Order đang điều tra không xuất hiện trong `related_order_ids`.
