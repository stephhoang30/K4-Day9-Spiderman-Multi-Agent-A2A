# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Nguyễn Hoàng Bảo Minh |
| MSSV            | 2A202601626 |
| Khóa/Lớp        | K4 - D305 |
| Vai trò chính   | Xây dựng pipeline multi-agent (orchestration LangGraph, business logic EC_POLICY_V2, tích hợp LLM đa-provider) và debug điểm số hệ chấm |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------- | ------------------- | --------------- | ---------------- | ---------- |
| Orchestration 7-agent (LangGraph) | `agents/coordinator.py`, `agents/*.py`, `agents/state.py` | `input/EC_0xx.json` | `AgentState` cuối cùng, gồm `verifier_result.case_output` | Hoàn thành |
| Business logic EC_POLICY_V2 | `core/policy_rules.py`, `core/evidence.py` | Kết quả 4 agent domain (customer/order_product/payment/delivery) | `primary_issue`, `secondary_issues`, refund, root cause, evidence_ids | Hoàn thành |
| Data access layer | `core/data_loader.py`, `core/customer.py`, `core/order_product.py`, `core/payment.py`, `core/delivery.py` | 7 CSV Olist (`data/`) | Domain object cho từng agent (items, payments, customer history, delivery variance) | Hoàn thành |
| LLM client đa-provider fallback | `llm/llm_client.py` | system/user prompt (tiếng Việt) | note diễn giải ghi vào `trace.jsonl` (không ảnh hưởng output chấm điểm) | Hoàn thành |
| Script vận hành | `scripts/run_pipeline.py`, `scripts/validate_output.py`, `scripts/package_output.py` | `input/`, `output/` | `output/EC_0xx.json`, `logging/trace.jsonl`, `output.zip` có version | Hoàn thành |

Toàn bộ 5 module trên phụ thuộc lẫn nhau theo đúng thứ tự: data access layer → domain agent → policy engine (business logic) → verifier (validate qua `core/schemas.py`) → script vận hành đóng gói kết quả cuối.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------ | -------- |
| Điền `architecture.md` (sơ đồ agent, vai trò, quyền truy cập, verification gate) | Toàn nhóm | File `architecture.md` đầy đủ 6 mục, khớp đúng code thật đã build |
| Đối chiếu độc lập README vs `core/policy_rules.py` (dùng 1 agent review riêng, không cho xem code trước) | Toàn nhóm | Xác nhận không có điểm hiểu sai rule nghiệp vụ so với README |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ----------------------------- | ------------------- | --------------- |
| Chạy pipeline thật trên 50 case | `scripts/run_pipeline.py` | `output/EC_001.json` .. `EC_050.json`, `logging/trace.jsonl` (300 dòng = 50 case × 6 agent) | `uv run python scripts/run_pipeline.py` |
| Tự kiểm tra output trước khi nộp | `scripts/validate_output.py` | Báo cáo PASS/FAIL từng case, kiểm tra evidence tồn tại thật trong CSV | `uv run python scripts/validate_output.py` → 50/50 PASS, 0 hard-gate |
| Tìm và fix root cause điểm chấm thấp | `core/order_product.py` | Điểm hệ chấm tăng từ 5.7036/100 lên **79.6977/100** | Nộp `output.zip` lên trang chấm điểm, so 2 lần chấm trước/sau fix |

Output cụ thể: file `output/EC_001.json` — case được phân loại `unsupported_late_claim` (giao sớm hơn dự kiến 166.52 giờ, payment khớp trong sai số 0.10 BRL), có đầy đủ `evidence_ids` trỏ tới order/item/payment thật trong CSV, đã qua `core.schemas.CaseOutput` validate không lỗi.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần việc của tôi là toàn bộ pipeline: nhận 50 case khiếu nại (`input/EC_0xx.json`), với mỗi case phải tự truy vấn 7 CSV Olist để dựng lại order/item/payment/seller/product/customer liên quan, áp đúng bảng quyết định `EC_POLICY_V2` (README mục 4) để xác định primary/secondary issue, bên chịu trách nhiệm, refund, root cause và evidence — sau đó ghi ra `output/EC_0xx.json` đúng schema, đúng giới hạn mảng, không có evidence bịa (false positive).

### Cách triển khai

- **Orchestration**: LangGraph `StateGraph` với DAG cố định (rule-based, không dùng LLM để routing): `order_product_agent` → (`customer_agent`, `payment_agent`, `delivery_agent` chạy song song) → `policy_agent` → `verifier_agent`. Mỗi agent là 1 node, state dùng `Annotated[list, operator.add]` cho field `trace` để các nhánh song song append an toàn.
- **Tách bạch số liệu và ngôn ngữ tự nhiên**: mọi phép tính bị chấm điểm nghiêm ngặt (đối soát payment, delivery variance, quyết định policy, evidence ID) là code Python thuần trong `core/*.py`, không giao cho LLM — tránh hallucination trên trường bị chấm. LLM (fallback 5 tầng: OpenRouter 3 model → NVIDIA NIM → Groq, đã verify gọi API thật) chỉ viết note diễn giải cho `trace.jsonl`.
- **Policy engine**: `core/policy_rules.py` áp đúng thứ tự ưu tiên 6 dòng trong bảng README (canceled/unavailable trước, rồi late_delivery_seller/logistics, rồi valid_split_payment/unsupported_late_claim), tính `confidence` bằng heuristic dựa trên khoảng cách tới ngưỡng quyết định (VD lệch giờ giao hàng càng xa 0 thì càng chắc chắn) thay vì giá trị cố định.
- **Evidence**: `core/evidence.py` chỉ dựng đúng 5 định dạng ID cho phép, seller trong evidence chỉ lấy seller "chịu trách nhiệm" (từ `responsible_parties`), không phải mọi seller của đơn.

### Input, output và contract

| Thành phần | Mô tả |
| ----------- | ------ |
| Input | `input/EC_0xx.json` theo schema README mục 3 (`case_id`, `customer_request.claimed_order_id`, `policy_version`) |
| Output | `output/EC_0xx.json` đúng `core.schemas.CaseOutput` (pydantic), giới hạn mảng theo README mục 6 |
| Module phụ thuộc | `core/data_loader.py` (đọc CSV), `core/policy_rules.py`, `core/evidence.py` |
| Module sử dụng output | `scripts/validate_output.py`, `scripts/package_output.py` (đóng gói `output.zip` để nộp) |
| Điều kiện lỗi cần xử lý | Order không có item row → `expected_total_brl/difference_brl/reconciled` phải `null`, các mảng item/seller/category rỗng; LLM 1 provider lỗi/treo → fallback provider kế tiếp (timeout 15s, tối đa 3 lần/provider) |

### Cách xác minh

```bash
uv run python scripts/run_pipeline.py
uv run python scripts/validate_output.py
uv run python scripts/package_output.py
```

- **Kết quả mong đợi:** 50/50 case ghi được output hợp lệ, không case nào fail hard-gate.
- **Kết quả thực tế:** `validate_output.py` báo PASS 50/50, 0 hard-gate, 0 vi phạm bất biến. Nộp thử `output.zip` lên hệ chấm đạt **79.6977/100** (sau khi fix bug mục 5), tăng từ 5.7036/100 ở lần nộp đầu.
- **Artifact/log:** `output/EC_001.json` .. `EC_050.json`, `logging/trace.jsonl`, `logging/metadata.json`, `submissions/output_v4_*.zip` (bản lưu vết).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** field output `product_context.category_names` nên lấy giá trị gì — dữ liệu Olist có cột gốc tiếng Bồ Đào Nha (`products.product_category_name`, VD `beleza_saude`) và 1 file dịch sẵn sang tiếng Anh (`product_category_name_translation.csv`, VD `health_beauty`). README không nói rõ dùng bản nào.
- **Các phương án đã cân nhắc:**
  1. Dịch sang tiếng Anh qua file translation — lý do ban đầu: "sạch"/dễ đọc hơn cho người chấm.
  2. Giữ nguyên giá trị gốc tiếng Bồ Đào Nha từ `products.csv`, không dịch.
- **Phương án đã chọn:** (2) — giữ nguyên tiếng Bồ Đào Nha.
- **Lý do:** tên field output `category_names` khớp trực tiếp với tên cột CSV gốc `product_category_name`, không khớp với cột đã dịch `product_category_name_english`; README không có chỗ nào yêu cầu dịch sang tiếng Anh. Việc tự thêm bước "dịch cho đẹp" là suy đoán ngoài đề bài.
- **Bằng chứng quyết định phù hợp:** sau khi đổi từ phương án (1) sang (2) và nộp lại `output.zip` (không đổi gì khác), điểm hệ chấm nhảy từ **5.7036/100 lên 79.6977/100** — 6/7 hạng mục con tăng đồng loạt chính xác **+74.0000 điểm** (VD "Entity liên quan" 6.0743 → 80.0743), cho thấy đây đúng là root cause chính, không phải trùng hợp.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `KeyError: 'payment_result'` khi gọi `graph.invoke(initial_state)`, xảy ra bên trong node `policy_agent` (traceback báo `During task with name 'policy_agent'`).
- **Lệnh hoặc bước tái hiện:** chạy `run_case(case_input)` cho 1 case bất kỳ (VD `EC_001`) ngay sau khi build xong DAG LangGraph với cấu trúc: `START` → (`customer_agent`, `order_product_agent`) song song → `order_product_agent` → (`payment_agent`, `delivery_agent`) → (`customer_agent`, `payment_agent`, `delivery_agent`) → `policy_agent`.
- **Nguyên nhân gốc:** `customer_agent` chỉ cách `START` 1 hop, trong khi `payment_agent`/`delivery_agent` cách `START` 2 hop (qua `order_product_agent`). LangGraph AND-join tại `policy_agent` không đợi đồng bộ theo "độ sâu" nếu các nhánh vào không cùng số superstep — `customer_agent` xong ở superstep 1 khiến `policy_agent` bị kích hoạt sớm, trước khi `payment_agent`/`delivery_agent` kịp chạy ở superstep 2, dẫn tới đọc field `state["payment_result"]` chưa tồn tại.
- **Cách xử lý:** đổi `agents/coordinator.py` để `customer_agent` cũng chạy SAU `order_product_agent` (thay vì song song thẳng từ `START`) — cân bằng cả 3 nhánh (`customer_agent`, `payment_agent`, `delivery_agent`) về cùng độ sâu 2 hop trước khi hội tụ tại `policy_agent`.
- **Cách xác minh sau khi sửa:** chạy lại `run_case()` cho `EC_001`, `EC_002`, `EC_003` — không còn `KeyError`, `verifier_result.valid == True` cho cả 3, sau đó chạy full 50 case thành công.
- **Điều học được:** LangGraph fan-out/fan-in (map-reduce pattern) yêu cầu các nhánh hội tụ vào cùng 1 node phải cùng "độ sâu" (số superstep) tính từ điểm rẽ nhánh chung gần nhất; nhánh ngắn hơn không tự động "chờ" nhánh dài hơn dù cả hai đều được khai báo là dependency của node đích.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của tôi (áp cho đúng bài lab Multi-Agent E-commerce Dispute Resolution):

1. **Dữ liệu đi từ CSV đến output như thế nào?** `input/EC_0xx.json` cho biết `claimed_order_id`. Order & Product Agent dùng ID này join `orders.csv` → `order_items.csv` → `products.csv`/`sellers.csv` để dựng item/seller/category; Customer Agent join `orders.customer_id` → `customers.customer_id` để lấy `customer_unique_id` rồi tìm các order khác cùng khách; Payment Agent join `order_payments.csv` theo `order_id`; Delivery Agent lấy trực tiếp các cột ngày trong `orders.csv` + `shipping_limit_date` trong item. Policy Agent tổng hợp 4 nhánh này để áp `EC_POLICY_V2`, Verifier Agent lắp ráp và validate schema trước khi Coordinator ghi `output/EC_0xx.json`.
2. **"Ground truth" ở đây là gì và dùng để đo chất lượng ra sao?** Không có ground-truth cho trước như các bài retrieval — "đúng" được định nghĩa hoàn toàn qua công thức tường minh trong README (VD `reconciled = abs(difference_brl) <= 0.10 BRL`). Tôi tự viết 1 script đối chiếu độc lập (không dùng lại code `core/`) để tính lại từ CSV gốc và so với output, dùng nó như một "oracle" thay cho ground-truth có sẵn.
3. **Quality check nào khác ngoài hard-gate?** Ngoài việc `Verifier Agent` chặn case sai schema/evidence không tồn tại (hard-gate), tôi còn tự viết `scripts/validate_output.py` kiểm tra thêm các bất biến nghiệp vụ không thể hiện qua pydantic một mình: rounding đúng 2 chữ số thập phân, `case_status` phải nhất quán với `recommended_refund_brl`, `valid_split_payment` không được kèm `verify_payment_allocation`.
4. **Vì sao phải dùng cùng 1 bộ 50 input cho mọi lần thử nghiệm/sửa lỗi?** Vì mọi so sánh điểm số trước/sau khi sửa (VD phát hiện lỗi category_names) chỉ có ý nghĩa nếu input không đổi — nếu đổi input giữa 2 lần đo, không thể biết chênh lệch điểm đến từ code hay từ dữ liệu khác nhau. Tôi luôn giữ nguyên `input/` khi thử nghiệm, chỉ đổi code.
5. **"Sửa đúng" được xem là thành công dựa trên artifact/metric nào?** Dựa trên 2 lớp: (a) `scripts/validate_output.py` báo PASS 50/50 không hard-gate (điều kiện cần), và (b) điểm thật từ hệ chấm bên ngoài khi nộp `output.zip` (điều kiện đủ) — vì (a) chỉ chứng minh output tự nhất quán, không chứng minh khớp đáp án gốc của hệ chấm.

**Câu trả lời:** (đã viết trực tiếp theo từng câu ở trên)

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hoàng Bảo Minh
**Ngày xác nhận:** 2026-08-05
