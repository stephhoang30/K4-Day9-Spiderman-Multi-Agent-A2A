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

## 2026-08-05 — Delivery Agent

### Contract đã chốt

Delivery Agent nhận `order` và `items` từ Order & Product Agent, sau đó trả ba timestamp giao hàng, `delivery_variance_hours`, `is_late_delivery`, `seller_handoff_analysis` và `late_handoff_seller_ids`.

- Delivery variance = `order_delivered_customer_date - order_estimated_delivery_date`.
- Với mỗi seller, handoff variance = `order_delivered_carrier_date - shipping_limit_date` sớm nhất của seller.
- Mọi giá trị giờ làm tròn 2 chữ số; thiếu timestamp thì variance là `null` và không kết luận trễ.
- Agent không chọn responsible party; Policy Agent sẽ dùng kết quả này để quyết định seller hay logistics.

## 2026-08-05 — Policy Agent

### Contract đã chốt

Policy Agent nhận handoff của Order & Product, Customer, Payment và Delivery Agent; trả `primary_issue`, `secondary_issues`, `case_status`, `root_cause_code`, `responsible_parties`, `recommended_refund_brl` và `resolution_actions`.

- Chọn primary theo đúng thứ tự ưu tiên `EC_POLICY_V2` trong README.
- Secondary issue theo thứ tự: multi item, multi seller, split payment, repeat customer, multiple categories.
- Action bổ sung theo thứ tự quy định; không thêm `verify_payment_allocation` khi primary là `valid_split_payment`.
- Không có rule phù hợp thì báo lỗi, không tự suy diễn nguyên nhân hoặc hoàn tiền.

## 2026-08-05 — Verifier Agent

### Contract đã chốt

Verifier Agent nhận JSON output ứng viên từ Coordinator và trả `is_valid` cùng danh sách `errors`, không tự sửa nội dung. Các kiểm tra gồm schema top-level, giới hạn array, confidence, timestamp, tính nhất quán phép đối soát tiền, root-cause code và evidence ID tham chiếu entity/policy trong output.

## 2026-08-05 — Coordinator Agent

### Luồng đã chốt

Coordinator nhận case, lấy `claimed_order_id`, rồi gọi theo thứ tự:

```text
Order & Product
  ├─ Customer
  ├─ Payment
  └─ Delivery
       ↓
     Policy
       ↓
  dựng output schema
       ↓
    Verifier
```

Coordinator dựng JSON output, cắt các array theo giới hạn README, tạo evidence ID từ entity/policy đã xác định và chỉ trả kết quả khi Verifier xác nhận hợp lệ. Đọc/ghi batch 50 file và trace là trách nhiệm của `orchestration/`.

## 2026-08-05 — Orchestration

`BatchRunner` đọc các file `EC_*.json`, gọi Coordinator cho từng case, ghi output cùng tên và ghi đè `logging/trace.jsonl` bằng trace của lượt chạy mới nhất. Trace chứa event bắt đầu/kết thúc/lỗi của Coordinator và handoff từ từng agent.

`logging/metadata.json` được tạo sau lượt chạy, ghi framework, Python runtime, thông tin model (không dùng LLM: `null`, `0`) và số case thành công/lỗi. CLI đặt tại `src/main.py`; mặc định yêu cầu đúng 50 case, `--allow-partial` chỉ dùng khi phát triển.
