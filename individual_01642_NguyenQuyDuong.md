# Member Role Report — Day 9: Multi-Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Quý Dương |
| MSSV | 01642 |
| Khóa/Lớp | K4 |
| Vai trò chính | Tích hợp LLM cục bộ, chạy batch và các tool phân tích dữ liệu xác định |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Lớp gọi model | `src/llm.py`: `chat()`, `extract_json()` | Prompt hệ thống/người dùng; cấu hình provider | Văn bản phản hồi hoặc JSON đã trích xuất cho routing và nhận xét verifier | Hoàn thành |
| Chạy từng case và batch | `src/run_case.py`, `src/run_all.py` | `input/EC_*.json`, bundle Olist | `output/EC_*.json`, trace của lượt chạy | Hoàn thành |
| Tool phân tích domain | `src/tools.py` | Bundle order, item, payment, customer, product | `delivery_analysis`, `payment_reconciliation`, `customer_context`, `product_context` | Hỗ trợ hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Thử nghiệm các biến thể đầu ra | `src/variants.py`, toàn bộ pipeline | Ghi lại ảnh hưởng từng biến thể; cải thiện điểm từ 79.1543 lên 91.8029 bằng việc chỉ giữ seller giao muộn trong `seller_handoff_analysis`. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Kết nối model ≤10B qua Ollama và xử lý phản hồi không thuần JSON | `src/llm.py` | Model `qwen3.5:4b` (4.7B, Q4_K_M); `chat()` trả `None` khi lỗi để pipeline dùng nhánh xác định | `logging/metadata.json`; trace lịch sử có `llm_route_accepted: "300/300"` |
| Sinh output cho toàn bộ bộ input | `src/run_all.py`, `src/run_case.py` | 50 output tương ứng 50 case; runner in rõ case và lỗi verifier nếu có | Lượt chạy lưu trong metadata: 50 case, 440.5 giây, 0 lỗi verifier |
| Tính delivery, payment và context từ dữ liệu CSV | `src/tools.py` | Các artifact xác định để Policy/Verifier sử dụng; không gọi model hay mạng | `tests/test_tools.py` có 11/11 kiểm tra lịch sử thành công |

Artifact cụ thể: `logging/metadata.json` của lượt chạy cuối ghi model `qwen3.5:4b`, `cases: 50`, `verifier_errors: 0`, `trace_lines: 650` và `leaderboard_score: 91.8029`.

> Lưu ý kiểm chứng: mã nguồn và 50 output của lượt chạy này thuộc commit `aa8a4fc`; checkout hiện tại chỉ còn metadata/trace, nên tôi không ghi nhận là đã chạy lại các lệnh dưới đây ở checkout hiện tại.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần dùng model cục bộ đúng giới hạn 10B để điều phối agent, nhưng các số tiền, chênh lệch thời gian, evidence ID và quyết định theo `EC_POLICY_V2` phải tái lập được. Nếu LLM trực tiếp tính các giá trị này, một phản hồi sai định dạng hoặc sai phép tính có thể làm output không hợp lệ.

### Cách triển khai

`src/llm.py` khai báo rõ model trong mã nguồn, đọc cấu hình provider từ môi trường và gọi Ollama theo API chat. `extract_json()` cắt phần object/array trong phản hồi rồi dùng `json.loads`; khi provider timeout, lỗi mạng, thiếu API key hoặc trả dữ liệu không hợp lệ, `chat()` trả `None` thay vì làm dừng batch.

`run_case()` lấy `claimed_order_id`, dựng bundle dữ liệu và gọi coordinator. `run_all.py` tải dữ liệu một lần, lần lượt xử lý các file `input/EC_*.json`, ghi JSON UTF-8 vào `output/` và cộng dồn lỗi verifier. Các tool trong `src/tools.py` giữ phần tính toán xác định: timestamp rỗng thành `null`, tiền làm tròn hai chữ số, đối soát payment với ngưỡng 0.10 BRL, và customer history dựa trên `customer_unique_id`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Case JSON có `case_id`, `customer_request.claimed_order_id`, `investigation_scope`, `policy_version`; dữ liệu Olist đã join thành bundle |
| Output | JSON theo schema của đề bài, cùng kết quả verifier `{result, errors}` ở mức runner |
| Module phụ thuộc | `src/datastore.py`, `src/agents.py`, `src/bus.py`, `src/variants.py` |
| Module sử dụng output | `src/policy.py`, `src/verifier.py`, `src/run_all.py` |
| Điều kiện lỗi cần xử lý | Provider không phản hồi, JSON model không parse được, timestamp rỗng, order không có item, và lỗi verifier trên từng case |

### Cách xác minh

```powershell
python src/run_all.py
python scripts/validate_output.py
python tests/test_tools.py
python tests/test_policy.py
```

- **Kết quả mong đợi:** 50 file JSON hợp lệ, verifier không báo lỗi và hai bộ test xanh.
- **Kết quả đã lưu:** `50 case xong trong 440.5s, 0 lỗi verifier`; `50 file, 0 lỗi`; `OK 11/11`; `OK 8/8`.
- **Artifact/log:** `logging/metadata.json`, `logging/trace.jsonl` của commit `aa8a4fc`; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** LLM nhỏ có thể chọn agent tiếp theo và tạo nhận xét, nhưng không đáng tin cậy để tính số tiền hoặc chênh lệch timestamp chính xác.
- **Các phương án đã cân nhắc:** (1) để LLM tự đọc dữ liệu và tính toàn bộ kết quả; (2) dùng LLM chỉ cho routing/nhận xét, còn code tính dữ liệu và áp policy xác định.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Cùng bundle luôn cho cùng output, dễ tái lập và có thể verifier đối chiếu với CSV; đồng thời vẫn có A2A routing thực tế qua LLM.
- **Bằng chứng:** Metadata ghi 300/300 route LLM được chấp nhận; biến thể test trong `src/variants.py` ghi điểm cuối 91.8029 sau khi sửa chính xác trường delivery.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Lượt routing ban đầu có thể rơi về `fallback_default_order` khi model trả danh sách agent thiếu một agent.
- **Bước tái hiện:** Chạy batch và đếm event routing có `source: "fallback_default_order"` trong `logging/trace.jsonl`.
- **Nguyên nhân gốc:** Prompt trước đó yêu cầu model nhỏ trả đủ bốn agent trong một phản hồi; model đôi khi bỏ sót `delivery`, khiến tập kết quả không thỏa điều kiện hợp lệ.
- **Cách xử lý:** Đổi sang yêu cầu chọn một agent ở mỗi bước, kèm danh sách agent chưa chạy và ràng buộc phụ thuộc. `extract_json()` hỗ trợ lấy object JSON khi model thêm văn bản bao quanh.
- **Cách xác minh sau khi sửa:** Artifact cuối ghi `llm_route_accepted: "300/300"` và `llm_review_returned: "50/50"`.
- **Điều học được:** Với model nhỏ, chia quyết định lớn thành các lựa chọn có ràng buộc rõ ràng đáng tin hơn việc yêu cầu một kế hoạch đầy đủ trong một lần gọi.

## 7. Hiểu biết về luồng end-to-end

1. `run_all.py` đọc từng input; `run_case.py` dùng `claimed_order_id` để lấy bundle từ CSV Olist. Bundle gồm order, item, payment, customer, product và seller theo các khóa join của dataset.
2. Coordinator cắt bundle thành các lát dữ liệu, rồi điều phối Customer, Order/Product, Payment và Delivery Agent. Mỗi agent tạo handoff artifact riêng; Policy Agent nhận các artifact để áp `EC_POLICY_V2`.
3. Các tool xác định tính delivery variance, seller handoff variance, tổng item/freight/payment và customer history. Vì thế LLM không được phép thay đổi các con số hoặc evidence.
4. Policy chọn primary issue theo thứ tự ưu tiên, sau đó thêm secondary issue và action. Verifier kiểm tra schema, array limit, evidence ID, null handling và tính nhất quán refund trước khi runner ghi file.
5. Kết quả cần đối chiếu bằng 50 JSON output, `logging/trace.jsonl` (650 dòng event) và `logging/metadata.json`. Cùng test set phải được giữ nguyên khi so baseline và biến thể để chênh lệch điểm chỉ phản ánh thay đổi đang thử, không phải khác biệt dữ liệu.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng ở checkout hiện tại.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Quý Dương  
**Ngày xác nhận:** 2026-08-05
