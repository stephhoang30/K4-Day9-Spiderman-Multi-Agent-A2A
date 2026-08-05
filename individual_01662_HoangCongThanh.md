# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung           |
| --------------- | ------------------ |
| Họ và tên       | Hoàng Công Thành   |
| MSSV            | 01662              |
| Khóa/Lớp        | K4 / D305          |
| Vai trò chính   | Developer          |
| Ngày hoàn thành | 2026-08-05         |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | --------------- | ---------- |
| Data layer | `src/datastore.py` — `load_all()`, `get_case_bundle()` | 9 file CSV Olist | 7 index tra cứu O(1), bundle 8 khoá cho mỗi order | Hoàn thành |
| Tool tính toán | `src/tools.py` — `analyze_delivery()`, `reconcile_payment()`, `build_customer_context()`, `build_product_context()` | bundle đã cắt lát | `delivery_analysis`, `payment_reconciliation`, `customer_context`, `product_context` | Hoàn thành |
| Luật nghiệp vụ | `src/policy.py` — `classify()` | kết quả 4 tool trên | primary/secondary issue, refund, actions, evidence | Hoàn thành |
| Điều phối agent | `src/agents.py` — `coordinator_agent()`, `_route()`, `_slices()`, `_policy_slice()` | input JSON + bundle | output cuối cùng 11 khoá | Hoàn thành |
| Bộ kiểm xác định | `src/verifier.py` — 12 luật | JSON đã dựng xong | danh sách lỗi | Hoàn thành |
| A2A bus + trace | `src/bus.py` — `send()`, `note()`, `reset_trace()` | envelope `{from,to,task,payload}` | `logging/trace.jsonl` | Hoàn thành |
| Đóng gói và kiểm tra | `scripts/validate_output.py`, `scripts/make_zip.py` | `output/*.json` | `output.zip` 50 entry | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Dựng nhật ký thí nghiệm với bộ chấm | cả nhóm | `src/variants.py` — mỗi biến thể một công tắc env, kèm số đo thật của từng lượt nộp |
| Đối chiếu lại tài liệu với code | `architecture.md`, `docs/CODELAB.md`, `docs/PHAN_CONG_CONG_VIEC.md` | sửa các con số và khẳng định sai (số test, số index, cơ chế chặn của verifier) |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Sinh 50 output đúng schema | `src/run_all.py` | 50 file `output/EC_001..050.json`, 0 lỗi verifier | `python scripts/validate_output.py` → `50 file, 0 lỗi` |
| Chuyển điều phối sang model | `src/agents.py:_route()` | 300/300 quyết định route do model đưa ra | `logging/trace.jsonl`, đếm `source == "llm_route"` |
| Test chốt hành vi | `tests/test_tools.py`, `tests/test_policy.py` | 19 assert phủ 6 primary issue và 4 tool | `python tests/test_tools.py` → `OK 11/11`; `python tests/test_policy.py` → `OK 8/8` |
| Đóng gói nộp bài | `scripts/make_zip.py` | `output.zip` đúng 50 entry `output/EC_0NN.json` | script tự chạy 12 luật trước khi nén, còn lỗi thì từ chối đóng gói |

Một output cụ thể phần việc của tôi tạo ra: **điểm trên bộ chấm đi từ 79.1543 lên 91.8029**. Mức tăng đến từ một thay đổi duy nhất trong `src/tools.py:analyze_delivery` — `seller_handoff_analysis` chỉ liệt kê seller giao muộn thay vì mọi seller của order. Cách tìm ra nó ghi ở mục 5.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Mỗi case phải đối chiếu 6 bảng CSV rồi kết luận: vấn đề chính là gì, ai chịu trách nhiệm, hoàn bao nhiêu tiền, bằng chứng nào. Rubric chấm 6/7 thành phần bằng con số và ID chính xác tuyệt đối — sai một ký tự trong evidence ID là false positive, sai phép trừ hai timestamp là mất 15%.

Ràng buộc đề bài: mỗi agent chỉ được dùng model ≤ 10B tham số. Model tôi dùng là `qwen3.5:4b` (4.7B, Q4_K_M, chạy local qua ollama).

### Cách triển khai

Quyết định trung tâm: **model điều phối, code sinh số**.

Model 4.7B trừ hai timestamp ra kết quả sai, và ngưỡng đối soát 0.10 BRL là luật cứng chứ không phải phán đoán. Nên toàn bộ con số trong output do code xác định sinh ra: `src/tools.py` tính chênh lệch giờ và đối soát tiền, `src/policy.py` chọn primary issue bằng chuỗi điều kiện dừng ở nhánh khớp đầu tiên theo đúng thứ tự ưu tiên của `EC_POLICY_V2`. Cùng một bundle thì luôn ra cùng một kết luận.

Model giữ hai việc thật:

1. **Điều phối.** `_route()` gọi model một lần cho mỗi bước, gửi danh sách agent đã chạy và chưa chạy, model trả `{"next": "<tên_agent>"}`. Coordinator không giữ sẵn thứ tự nào; nó chỉ giữ bảng phụ thuộc `DEPENDS` và từ chối lựa chọn chưa đủ đầu vào — `policy_agent` cần đủ 4 agent dữ liệu, `verifier_agent` cần kết luận của `policy_agent`.
2. **Nhận xét kết luận.** Verifier gọi model để lấy một câu đánh giá, ghi vào trace.

Ranh giới truy cập dữ liệu là cơ chế thật chứ không phải quy ước. Coordinator cắt bundle thành các lát trong `_slices()` trước khi gửi, nên Payment Agent không thấy bảng `orders` và không thể tự suy ra kết luận giao hàng, còn Delivery Agent không thấy `payments` nên không thể tự quyết số tiền hoàn. `_policy_slice()` chỉ gửi cho Policy Agent 5 trường mà `src/policy.py` thực sự đọc tới.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | `input/EC_0NN.json` — `case_id`, `customer_request.claimed_order_id`, `investigation_scope`, `policy_version` |
| Output | `output/EC_0NN.json` — 11 khoá cấp một theo README mục 6, giới hạn mảng 5/5/3/5/5/5/5/3/3/20/5 |
| Module phụ thuộc | `src/datastore.py` (index CSV), `src/llm.py` (gọi model) |
| Module sử dụng output | `src/verifier.py` (12 luật), `scripts/make_zip.py` (đóng gói) |
| Điều kiện lỗi cần xử lý | order không có item row (775 order trong CSV): 3 trường tiền phải là `null`, các mảng item/seller/product/category/seller handoff phải rỗng; timestamp rỗng trong CSV phải thành `null` chứ không phải 0; `round()` trên số thực có thể ra `-0.0` nên phải chuẩn hoá về `0.0` |

### Cách xác minh

```bash
python src/run_all.py && python scripts/validate_output.py && python tests/test_tools.py && python tests/test_policy.py
```

- **Kết quả mong đợi:** 50 case chạy xong không lỗi verifier, 50 file hợp lệ, hai bộ test xanh.
- **Kết quả thực tế:** `50 case xong trong 440.5s, 0 lỗi verifier` / `50 file, 0 lỗi` / `OK 11/11` / `OK 8/8`. Điểm bộ chấm 91.8029.
- **Artifact/log:** `logging/trace.jsonl` (650 dòng, 13 dòng mỗi case), `logging/metadata.json`, `output.zip`. Không chứa secret; API key nếu có nằm trong `.env` và `.gitignore` đã chặn.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `delivery_analysis.seller_handoff_analysis` nên liệt kê mọi seller của order, hay chỉ seller giao muộn? README mục 6 chỉ đưa ví dụ một order có một seller nên không phân định được. Điểm đang đứng ở 79.1543 và không biết 20 điểm còn lại mất ở đâu.
- **Các phương án đã cân nhắc:** (a) đoán rồi thử lần lượt từng trường; (b) đo trước để thu hẹp vùng nghi vấn, rồi mới thử.
- **Phương án đã chọn:** (b). Đo riêng biến thể `NULL_MONEY` — chỉ chạm 6 case không có item row. Điểm rơi 79.1543 → 67.00, tức mỗi case đó mất ~101 điểm, nghĩa là nhóm này vốn đã được ~100/100. Vì tổng là 79.1543, suy ra 44 case *có* item row chỉ đang được ~76.3. Toàn bộ điểm mất nằm ở một trường dẫn xuất từ item. Trong các ứng viên thì `seller_handoff_analysis` phủ rộng nhất nên thử trước.
- **Lý do:** mỗi lượt nộp cách nhau 120 giây và điểm mới thay thế điểm cũ, nên số lượt là tài nguyên khan hiếm. Một phép đo thu hẹp được vùng nghi vấn đáng giá hơn ba lần đoán mò.
- **Bằng chứng quyết định phù hợp:** 79.1543 → **91.8029**. Toàn bộ nhật ký đo nằm trong docstring `src/variants.py`, gồm cả các biến thể bị bác bỏ: evidence thừa −0.68, `confidence = 0.92` −0.01, gộp ba thay đổi cuối −43.03.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `logging/trace.jsonl` ghi `"source": "fallback_default_order"` cho cả 50 case và `"llm_review": null` cho cả 50 case, mọi `latency_ms` bằng 0. Trace nộp kèm là bằng chứng cho thấy model không hề tham gia, trong khi `metadata.json` khai 2 lời gọi model mỗi case.
- **Lệnh tái hiện:** `python src/run_all.py` rồi đếm `grep -c fallback_default_order logging/trace.jsonl` → 50.
- **Nguyên nhân gốc:** không phải ollama hỏng. Prompt Coordinator lúc đó hỏi model một lần để lấy cả 4 tên agent cùng lúc; model 4.7B trả về 3 tên, bỏ mất `delivery`. Hàm `_plan()` kiểm tra tập trả về phải đúng bằng 4 tên nên loại kết quả và rơi về mặc định — đúng logic, nhưng khiến model không đóng góp gì.
- **Cách xử lý:** đổi từ hỏi một lần sang hỏi từng bước. Mỗi lần model chỉ phải chọn **một** tên trong danh sách chưa chạy, kèm ràng buộc phụ thuộc ghi rõ trong system prompt.
- **Cách xác minh sau khi sửa:** chạy lại 50 case, đếm `source == "llm_route"` trong trace → **300/300**, không lần nào rơi về fallback. Cùng lúc, `LLM_ENABLED=0` vẫn cho ra 50 output không đổi một byte, chứng minh model điều phối chứ không sinh số.
- **Điều học được:** với model nhỏ, chia một quyết định lớn thành nhiều quyết định nhỏ đáng tin hơn là siết prompt. Và trace phải được đọc chứ không chỉ được ghi — file trace vẫn "đầy đủ 400 dòng" trong khi thứ nó ghi lại là model không làm gì.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ `input/EC_0NN.json` đến `output/EC_0NN.json` như thế nào?
2. Handoff giữa các agent diễn ra ở đâu, và bằng chứng nào cho thấy nó là thật chứ không phải tên gọi?
3. Bộ kiểm xác định khác nhận xét của model ở điểm nào?
4. Vì sao mỗi lượt thử biến thể chỉ được đổi đúng một thứ?
5. Dựa vào artifact và metric nào để kết luận một thay đổi là cải thiện?

**Câu trả lời:**

1. `run_all.py` đọc `claimed_order_id` từ input, `get_case_bundle()` tra 7 index đã dựng sẵn từ CSV để gom order, item, payment, customer, product, seller. Coordinator cắt bundle thành các lát và lần lượt gọi 4 agent dữ liệu; mỗi agent chạy tool xác định của nó. Policy Agent nhận kết quả 4 agent đó cộng 5 trường tối thiểu của order rồi áp `EC_POLICY_V2`. Coordinator gộp thành output 11 khoá, Verifier chạy 12 luật, `run_all.py` ghi file.

2. Handoff nằm ở `bus.send()`. Không agent nào gọi thẳng agent khác — mọi lần chuyển việc đều đi qua một envelope `{from, to, task, payload}` và bus ghi lại một dòng trace kèm `payload_keys`, `result_keys`, `status`, `latency_ms`. Bằng chứng handoff là thật: ranh giới truy cập được thực thi bằng cơ chế chứ không phải quy ước — Payment Agent không nhận được bảng `orders` trong lát của nó nên không thể tự kết luận về giao hàng, dù có muốn.

3. Bộ kiểm xác định là 12 luật trong `src/verifier.py`, đối chiếu từng evidence ID với CSV thật và kiểm giới hạn mảng, định dạng timestamp, tính nhất quán giữa `case_status` và refund. Nhận xét của model chỉ được ghi vào trace và không có quyền lật kết luận. Lý do rất cụ thể: bản đầu định để model phán "output này có hợp lệ không", và model 4.7B duyệt qua cả file có evidence sai định dạng. Chèn tay `evidence_ids[1] = "item:1"` thì bộ kiểm báo `luat 7` và `luat 8`.

4. Vì delta chỉ đọc được khi có một biến số. Lượt 1 của nhóm bật bốn biến thể cùng lúc, điểm rơi 12.45, và nhật ký quy trách nhiệm cho `NULL_MONEY` — về sau đo riêng mới thấy `NULL_MONEY` chiếm −12.15 còn `CONF_ONE` chỉ −0.01, tức kết luận ban đầu đúng nhưng lý do ghi kèm thì không có cơ sở. Lượt V2 gộp ba thay đổi, mất 43.03 điểm mà không tách được thủ phạm, và hết lượt nộp nên đến giờ vẫn chưa biết cái nào sai.

5. Ba thứ, theo thứ tự: `python scripts/validate_output.py` phải ra 0 lỗi (điều kiện cần, không phải điều kiện đủ); hai bộ test phải xanh; và cuối cùng là điểm trên bộ chấm. Chỉ điểm bộ chấm mới nói được một thay đổi là cải thiện — verifier chỉ bắt được lỗi schema, không bắt được việc điền đúng định dạng nhưng sai nội dung. `seller_handoff_analysis` liệt kê mọi seller vượt qua cả 12 luật và vẫn làm mất 12.65 điểm.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:**
**Ngày xác nhận:**
