# Agent giao hàng

Tính chênh lệch thời gian giao hàng và thời điểm seller bàn giao cho đơn vị vận chuyển.

## Contract bàn giao

`DeliveryAgent().investigate(order, items)` nhận `order` và `items` từ Order & Product Agent, trả:

- ba timestamp gốc: `delivered_at`, `estimated_delivery_at`, `carrier_handoff_at`;
- `delivery_variance_hours`, `is_late_delivery`;
- `seller_handoff_analysis` và `late_handoff_seller_ids`.

Với mỗi seller, agent dùng `shipping_limit_date` sớm nhất trong các item của seller. Các chênh lệch được tính theo giờ và làm tròn 2 chữ số. Nếu thiếu một trong hai timestamp cần so sánh, chênh lệch là `null` và không kết luận trễ.
