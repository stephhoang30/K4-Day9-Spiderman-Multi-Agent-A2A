# Tiến trình thiết kế kiến trúc

> File này ghi lại các quyết định kiến trúc đã thống nhất trong quá trình làm bài Day 9. Chỉ ghi quyết định đã chốt, không ghi API key, secret hoặc dữ liệu nhạy cảm.

## 2026-08-05 — Khởi tạo cấu trúc mã nguồn

### Mục tiêu bài toán

Xây dựng hệ thống multi-agent điều tra khiếu nại thương mại điện tử trên dữ liệu Olist. Hệ thống nhận từng case, đối soát dữ liệu, áp dụng `EC_POLICY_V2` và tạo JSON kết quả đúng schema của đề bài.

### Cấu trúc thư mục đã tạo

```text
src/
├── agents/
│   ├── coordinator/
│   ├── customer/
│   ├── order_product/
│   ├── payment/
│   ├── delivery/
│   ├── policy/
│   └── verifier/
├── orchestration/
└── shared/
```

- `agents/`: logic nghiệp vụ tách theo từng domain.
- `shared/`: contract bàn giao, schema, đọc dữ liệu và tiện ích dùng chung.
- `orchestration/`: định tuyến case, thứ tự gọi agent, chạy batch và ghi trace.

### Thứ tự triển khai dự kiến

1. `order_product`
2. `customer`, `payment`, `delivery`
3. `policy`
4. `verifier`
5. `coordinator`

`Order & Product Agent` được làm đầu vì nó cung cấp thông tin order và item nền tảng cho các agent tiếp theo.

### Quyết định về LLM

Các phép join CSV, tính tiền, tính thời gian và áp policy sẽ thực hiện bằng Python có tính xác định. Không bắt buộc dùng LLM cho các tác vụ này. Nếu bổ sung LLM, model của mỗi agent phải có tối đa 10B tham số theo README và phải được khai báo trong source cùng `logging/metadata.json`.

### Contract của Order & Product Agent

Agent nhận `order_id` và chỉ bàn giao trường cần thiết, không chuyển nguyên record CSV:

```text
order:
  order_id
  customer_id
  order_status
  order_delivered_carrier_date
  order_delivered_customer_date
  order_estimated_delivery_date

items[]:
  item_id
  order_item_id
  product_id
  seller_id
  shipping_limit_date
  price
  freight_value
  category_name

seller_ids[]
product_ids[]
category_names[]
```

Các danh sách ID/category là unique và giữ thứ tự xuất hiện trong CSV. Với order không có item, các mảng liên quan trả về rỗng.

### Quyết định về định danh khách hàng

- `customer_id` được lấy từ bảng `orders` và bàn giao cho Customer Agent.
- `customer_unique_id` không thuộc Order & Product Agent.
- Customer Agent sẽ join `orders.customer_id -> customers.customer_id` để lấy `customer_unique_id`, sau đó tìm các đơn lịch sử cùng khách.

Lý do: `customer_id` đại diện cho một order trong dữ liệu Olist; `customer_unique_id` mới định danh cùng một khách qua nhiều order.

## 2026-08-05 — Customer Agent

### Contract đã chốt

Customer Agent nhận `customer_id` và `claimed_order_id` từ case/handoff trước, sau đó join sang bảng customers để trả:

```text
customer_unique_id
related_order_ids      # tối đa 5, không gồm claimed_order_id
related_order_count    # số lượng trước khi giới hạn 5
is_repeat_customer
```

Agent xác nhận claimed order thực sự thuộc customer được bàn giao. `related_order_ids` giữ thứ tự nguồn CSV và chỉ dùng cho `customer_context`, không được đưa vào `affected_entities`.

## 2026-08-05 — Payment Agent

### Contract đã chốt

Payment Agent nhận `order_id` cùng `items` từ Order & Product Agent, đọc payment row và trả:

```text
currency = BRL
payment_ids, payment_count, payment_types, is_split_payment
item_total_brl, freight_total_brl, expected_total_brl
payment_total_brl, difference_brl, reconciled
```

- Dùng `Decimal`; số tiền trả ra làm tròn 2 chữ số thập phân.
- `is_split_payment` là true khi có ít nhất 2 payment row.
- Nếu order không có item thì item/freight/expected/difference/reconciled là `null`, theo yêu cầu README.
