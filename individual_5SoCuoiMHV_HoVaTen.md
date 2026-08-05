# Member Role Report — Day 9: Multi Agent A2A

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Hồ Văn Tâm                              |
| MSSV            | 01542                                  |
| Khóa/Lớp        | K4                                     |
| Vai trò chính   | Tích hợp pipeline và kiểm thử/Verifier |
| Ngày hoàn thành | 2026-08-05                             |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái                            |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Tích hợp luồng chạy 7 agent và ghi kết quả atomic | `src/dispute_agents/orchestrator.py`, `src/dispute_agents/agents.py`, `src/dispute_agents/__main__.py` | 50 file `input/EC_*.json`, dữ liệu Olist và artifact của từng agent | 50 file `output/EC_*.json`, `logging/trace.jsonl`, `logging/metadata.json` | Hoàn thành |
| Kiểm tra output theo schema và kết quả `EC_POLICY_V2` deterministic | `src/dispute_agents/validation.py`, `tests/test_validation.py`, `tests/test_policy.py` | `CaseInput`, `CaseOutput` và snapshot chuẩn | `VerificationResult`; validation hợp lệ cho 50/50 case | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| Rà soát kiến trúc và tài liệu chạy/nộp bài | Toàn bộ pipeline, `README.md`, `architecture.md` | Đồng bộ mô tả 7 agent, provider, lệnh run/validate và artifact bàn giao |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Điều phối Customer → Order Product → Payment → Delivery → Policy → Coordinator → Verifier trên một snapshot | `src/dispute_agents/agents.py`, `src/dispute_agents/policy.py` | Handoff có schema, chỉ ghi output sau khi Verifier chấp nhận | `$env:PYTHONPATH='src'; python -m dispute_agents validate` |
| Chạy và kiểm tra bộ kết quả nộp bài | `output/`, `logging/trace.jsonl`, `logging/metadata.json` | 50 JSON hợp lệ; 1.050 sự kiện trace; metadata `success=true`, `case_count=50` | `Validation passed: output file set and all 50 case contracts are valid.` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Bộ bàn giao hiện có đủ `output/EC_001.json` đến `output/EC_050.json`. Lượt chạy OpenRouter dùng `openai/gpt-4o-mini`, hoàn tất 50 case và ghi 1.050 sự kiện có thứ tự vào `logging/trace.jsonl`; `logging/metadata.json` ghi `success=true`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần tích hợp giải quyết việc biến các kết quả domain rời rạc thành một `CaseOutput` nhất quán, có thể truy vết và chỉ được ghi ra đĩa sau khi vượt qua kiểm tra schema, evidence, tiền hoàn, null handling, giới hạn mảng và toàn bộ quy tắc `EC_POLICY_V2`.

### Cách triển khai

Mỗi case được join từ `claimed_order_id` và materialize đúng một lần thành `CaseSnapshot`. Năm domain agent lần lượt nhận lát dữ liệu có schema và handoff artifact cho agent kế tiếp. Policy Agent áp dụng nhánh primary theo thứ tự ưu tiên, sau đó thêm secondary issues và actions theo thứ tự cố định. Coordinator dựng `CaseOutput`; Verifier kiểm tra evidence bằng biểu thức định dạng và so sánh toàn bộ output với kết quả deterministic. Chỉ output hợp lệ mới được ghi atomic qua file tạm rồi đổi tên. Lượt chạy nhiều case dùng semaphore với concurrency mặc định là 5.

### Input, output và contract

| Thành phần              | Mô tả                                  |
| ----------------------- | -------------------------------------- |
| Input                   | `CaseInput`, `claimed_order_id`, 9 CSV Olist và `EC_POLICY_V2` |
| Output                  | `CaseOutput` cho từng case, `VerificationResult`, trace và metadata |
| Module phụ thuộc        | `repository.py`, `services.py`, `policy.py`, `models.py` |
| Module sử dụng output   | `orchestrator.py`, `validation.py`, CLI trong `__main__.py` |
| Điều kiện lỗi cần xử lý | Evidence sai/không tồn tại, refund lệch, order không có item, vượt giới hạn mảng, output khác kết quả deterministic hoặc provider trả artifact đã bị thay đổi |

### Cách xác minh

```powershell
$env:PYTHONPATH='src'
python -m dispute_agents validate
```

- **Kết quả mong đợi:** Có đúng 50 file JSON và tất cả case đúng schema, evidence cùng kết quả deterministic của `EC_POLICY_V2`.
- **Kết quả thực tế:** `Validation passed: output file set and all 50 case contracts are valid.`
- **Artifact/log:** `output/`, `logging/trace.jsonl`, `logging/metadata.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** LLM có thể tạo output đúng JSON schema nhưng vẫn bịa evidence, tính sai tiền hoặc đổi thứ tự policy.
- **Các phương án đã cân nhắc:** (1) để từng LLM tự đọc CSV và tự tính toàn bộ kết quả; (2) materialize dữ liệu một lần bằng code deterministic, dùng agent để handoff có schema rồi xác minh output cuối với snapshot chuẩn.
- **Phương án đã chọn:** Phương án 2: snapshot deterministic là nguồn dữ liệu có thẩm quyền; output của agent không được phép thay đổi artifact nhận vào.
- **Lý do:** Tăng correctness và reproducibility, giảm số lần join CSV và giảm nguy cơ hallucination; đổi lại LLM có ít quyền tự quyết hơn.
- **Bằng chứng quyết định phù hợp:** `tests/test_validation.py` có case cố ý sửa refund và evidence giả đều bị từ chối; lệnh validation hiện xác nhận đủ 50/50 case hợp lệ.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `D:\Python\python.exe: No module named dispute_agents`.
- **Lệnh hoặc bước tái hiện:** Chạy `python -m dispute_agents validate` khi package chưa được cài editable.
- **Nguyên nhân gốc:** Repo dùng cấu trúc `src/`; Python hiện tại chưa có `src` trong module search path.
- **Cách xử lý:** Đặt `$env:PYTHONPATH='src'` cho phiên PowerShell trước khi gọi module; khi setup đầy đủ có thể dùng `python -m pip install -e ".[dev]"`.
- **Cách xác minh sau khi sửa:** Chạy lại `$env:PYTHONPATH='src'; python -m dispute_agents validate` và nhận `Validation passed: output file set and all 50 case contracts are valid.`
- **Điều học được:** Với Python project dùng `src` layout, cần cài package hoặc khai báo đường dẫn import trước khi chạy CLI trực tiếp từ source.

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** Không áp dụng; blocker trên đã được xử lý.
- **Những gì đã loại trừ:** Không áp dụng; dữ liệu và output không phải nguyên nhân.
- **Bước tiếp theo:** Cài editable dependencies trước lần chạy mới để không cần đặt `PYTHONPATH` thủ công.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. `case_id` và `claimed_order_id` được dùng để truy xuất, join các bảng Olist như thế nào?
2. Customer, Order/Product, Payment và Delivery Agent tạo artifact gì và handoff ra sao?
3. `EC_POLICY_V2` chọn primary issue, responsible party, refund và action theo thứ tự nào?
4. Verifier ngăn evidence false-positive, sai số tiền, sai null handling và vượt array limit ra sao?
5. Dùng output, `trace.jsonl`, `metadata.json` và lệnh validation nào để tái hiện kết quả 50 case?

**Câu trả lời:**

1. CLI đọc từng `CaseInput`; `case_id` dùng để ghép đúng input, output và trace, còn `claimed_order_id` là khóa truy vấn order. Từ order, hệ thống nối `customer_id` sang bảng customer; nối `order_id` sang item và payment; từ item nối tiếp `product_id` và `seller_id`. `customer_unique_id` được dùng để tìm các order lịch sử của cùng khách nhưng không đưa chúng vào `affected_entities`.
2. Customer Agent tạo `CustomerContext`; Order Product Agent tạo `OrderProductFinding` và product context; Payment Agent tạo `PaymentReconciliation`; Delivery Agent tạo `DeliveryAnalysis`. Các artifact Pydantic được handoff tuần tự cho Policy Agent, sau đó Coordinator ghép thành `CaseOutput` và Verifier quyết định có cho phép ghi file hay không.
3. `EC_POLICY_V2` chọn primary theo thứ tự: canceled có payment, unavailable có payment, giao trễ do seller, giao trễ do logistics, split payment hợp lệ, rồi claim giao trễ không được dữ liệu hỗ trợ. Responsible party và refund phụ thuộc primary: platform hoàn toàn bộ payment, seller/logistics hoàn freight, hoặc không hoàn. Action chính được thêm trước, rồi mới đến action bổ sung theo secondary issues.
4. Verifier đối chiếu evidence với năm định dạng cho phép, cấm ID trùng và so sánh toàn bộ output với kết quả deterministic nên evidence giả hay refund sai đều bị chặn. `CaseOutput` dùng Pydantic `extra="forbid"` và `Field(max_length=...)` để chặn sai schema/vượt giới hạn. Với order không có item, service trả `expected_total_brl`, `difference_brl`, `reconciled` là `null` và các mảng item/seller/product rỗng.
5. Mỗi `output/EC_*.json` là kết quả cuối; `logging/trace.jsonl` ghi `run_id`, sequence, agent, event, trạng thái và digest artifact; `logging/metadata.json` ghi provider, model, runtime, số case và trạng thái lượt chạy. Để tái hiện kiểm tra 50 case, chạy `$env:PYTHONPATH='src'; python -m dispute_agents validate`; kết quả hiện tại xác nhận đủ 50 file và tất cả contract hợp lệ.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hồ Văn Tâm
**Ngày xác nhận:** 2026-08-05
