# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Trần Văn Ngọc |
| MSSV | [Điền MSSV đầy đủ; 5 số cuối: 01512] |
| Khóa/Lớp | K4 |
| Vai trò chính | Điều phối pipeline, data contract và kiểm chứng output |
| Ngày hoàn thành | 2026-08-05 |

## 2. Phạm vi công việc

| Module/deliverable | Input | Output bàn giao |
|---|---|---|
| `src/shared/data_repository.py` | CSV Olist | Index read-only dùng chung cho agent |
| `src/agents/*` | Handoff theo domain | Customer, payment, delivery, policy và verifier handoff |
| `src/agents/coordinator/agent.py` | Case JSON | Output schema đã qua verifier |
| `src/orchestration/runner.py` | 50 input case | 50 output, trace và metadata |

## 3. Kết quả và cách xác minh

- Batch xử lý thành công 50/50 case, không có lỗi.
- `output/` có đúng 50 file `EC_001.json`–`EC_050.json`.
- `logging/trace.jsonl` ghi triage, handoff của các agent và trạng thái hoàn tất/lỗi.
- Verifier đối chiếu evidence với CSV, chặn được item evidence không tồn tại.

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python src/main.py
```

## 4. Giải thích kỹ thuật

### Pipeline

Coordinator kiểm tra `policy_version` và `investigation_scope`, sau đó gọi Order & Product Agent. Handoff order/item được dùng song song bởi Customer, Payment và Delivery Agent. Policy Agent áp `EC_POLICY_V2`; Coordinator dựng JSON; Verifier kiểm tra schema, giới hạn, số tiền và evidence trước khi runner ghi output.

### Contract quan trọng

- Payment dùng `Decimal`: `expected_total_brl = sum(price) + sum(freight_value)`.
- Delivery group item theo seller và dùng `shipping_limit_date` sớm nhất của seller.
- Customer dùng `customer_unique_id`, không dùng `customer_id`, để tìm lịch sử order.
- Evidence chỉ dùng các dạng ID dựng trực tiếp từ CSV hoặc policy code.

## 5. Quyết định kỹ thuật

**Chọn xử lý rule-based cho dữ liệu và policy.** Các timestamp, tổng tiền và quyết định refund cần khả năng tái lập; dùng LLM cho các phép tính này có nguy cơ hallucination. Kiến trúc vẫn multi-agent vì mỗi agent có domain, handoff và bước verifier độc lập. Nếu cần LLM, nó phù hợp nhất với triage/presentation, không thay thế policy tính tiền.

## 6. Lỗi/blocker đã xử lý

CSV category translation có UTF-8 BOM ở header làm `DictReader` không tìm thấy `product_category_name`. Cách xử lý là đọc CSV bằng `utf-8-sig`. Sau sửa, Order & Product Agent join product/category thành công.

## 7. Hiểu biết end-to-end

1. Input cung cấp `claimed_order_id`; DataRepository join order, customer, item, payment, product và seller theo khóa Olist.
2. Customer/Payment/Delivery tạo handoff độc lập; Policy tổng hợp để chọn issue, refund và actions theo thứ tự ưu tiên.
3. Verifier kiểm tra output schema, giới hạn, công thức tiền, evidence và record nguồn trước khi ghi file.
4. Trace là bằng chứng orchestration: triage, handoff, lỗi hoặc hoàn tất của từng case.
5. Một batch thành công cần đủ 50 JSON hợp lệ, trace mới nhất và metadata runtime không chứa secret.

## 8. Cam kết

- [ ] Tôi đã thay MSSV đầy đủ trước khi nộp.
- [ ] Tôi có thể giải thích data contract, policy và các phép tính chính.
- [ ] Tôi không ghi API key, token hoặc secret vào repo/report.
- [ ] Tôi chỉ xác nhận các lệnh và artifact đã thực sự kiểm chứng.
