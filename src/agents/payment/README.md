# Agent thanh toán

Đối soát các dòng thanh toán với tổng giá trị item và phí vận chuyển.

## Contract bàn giao

`PaymentAgent(data_dir).investigate(order_id, items)` nhận danh sách `items` từ Order & Product Agent và trả:

- `payment_ids`, `payment_count`, `payment_types`, `is_split_payment`;
- `item_total_brl`, `freight_total_brl`, `expected_total_brl`;
- `payment_total_brl`, `difference_brl`, `reconciled`; và `currency = "BRL"`.

Tiền được tính bằng `Decimal`, làm tròn 2 chữ số thập phân. Nếu order không có item, các trường expected/difference/reconciled và tổng item/freight là `null` theo README.
