 # Kế hoạch triển khai: Hệ thống Multi-Agent xử lý tranh chấp Olist

  ## Tóm tắt

  Phân loại: Add Feature trên repository scaffold hiện có. Hoàn thiện pipeline CLI deterministic để xử lý từng case hoặc toàn bộ 50 case theo
  EC_POLICY_V2, validate trước khi ghi JSON, và tạo trace/metadata.

  ## Quy ước và interface

  - main.py là entry point CLI: nhận đường dẫn case hoặc chế độ batch; ghi JSON theo case_id vào output/.
  - DataLoader cung cấp DataFrame cache với tên logic ánh xạ đúng CSV olist_*_dataset.csv.
  - Mỗi agent nhận context/repository chỉ đọc và trả về handoff typed; chỉ Coordinator ghép handoff.
  - InputCase.model_validate_json() đọc input; CaseOutput.model_dump(mode="json") dùng để ghi output.
  - Thêm tests/ cho test unit, integration và batch; không thêm dependency ngoài requirements.txt hiện có.

  ## Yêu cầu EARS

  - R1: WHEN nhận input hợp lệ, hệ thống SHALL điều phối đúng Customer → Order → Payment → Delivery → Policy → Verifier.
  - R2: WHEN phân tích dữ liệu, mỗi agent SHALL chỉ truy vấn các bảng được cấp trong architecture.md.
  - R3: WHEN áp dụng EC_POLICY_V2, hệ thống SHALL chọn issue, refund, evidence và action theo đúng thứ tự README.
  - R4: WHEN thiếu item/timestamp, hệ thống SHALL trả null hoặc mảng rỗng đúng schema và không suy diễn.
  - R5: WHEN output được tạo, Verifier SHALL kiểm tra schema, ID, giới hạn mảng, confidence và hoàn tiền trước khi ghi.
  - R6: WHEN chạy batch, hệ thống SHALL ghi đúng output per case, trace lần chạy mới nhất và metadata.

  ## Thiết kế

  sequenceDiagram
      participant CLI as main.py
      participant C as Coordinator
      participant R as Repository
      participant A as Domain agents
      participant P as Policy
      participant V as Verifier

      CLI->>C: InputCase
      C->>R: dữ liệu Olist chỉ đọc
      C->>A: customer/order/payment/delivery
      A-->>C: handoff typed
      C->>P: handoff tổng hợp
      P-->>C: quyết định policy
      C->>V: CaseOutput draft
      V-->>C: output hợp lệ
      C-->>CLI: JSON cuối cùng

   Phương án                     Ưu điểm                                 Nhược điểm                                 Độ phức tạp    Khuyến nghị
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━  ━━━━━━━━━━━━━
   Agent Python deterministic    Tái lập được, đúng rubric, test được    Không suy luận ngôn ngữ tự do              Thấp           ✅
  ────────────────────────────  ──────────────────────────────────────  ─────────────────────────────────────────  ─────────────  ─────────────
   Agent gọi LLM                 Diễn giải linh hoạt                     Không xác định, cần key/model, khó chấm    Cao            ❌

   Edge case                    Hành vi
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Không tìm thấy order         Báo lỗi case, không ghi output không có căn cứ
  ───────────────────────────  ────────────────────────────────────────────────
   Không có item                Các total liên quan là null, mảng entity rỗng
  ───────────────────────────  ────────────────────────────────────────────────
   Timestamp thiếu              Timestamp/variance là null, không kết luận trễ
  ───────────────────────────  ────────────────────────────────────────────────
   Nhiều item/seller/payment    Giữ thứ tự CSV và giới hạn theo schema
  ───────────────────────────  ────────────────────────────────────────────────
   Input/output không hợp lệ    Dừng case với lỗi chi tiết, không ghi JSON

   Ngoại lệ                     Xử lý
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   CSV thiếu hoặc sai header    Fail fast lúc nạp dữ liệu
  ───────────────────────────  ────────────────────────────────
   JSON input sai               Báo validation error theo case
  ───────────────────────────  ────────────────────────────────
   Verifier từ chối output      Không ghi file; nêu rõ vi phạm
  ───────────────────────────  ────────────────────────────────
   Một case batch lỗi           Log lỗi và tiếp tục case khác

  Không có shared state ghi hoặc truy cập đồng thời; pipeline đồng bộ, CSV cache chỉ đọc. Output theo case_id được ghi đè có chủ đích, còn trace.jsonl
  được tạo mới mỗi batch, nên batch có thể chạy lại an toàn.

  ## Task hierarchy

  ### 1. Nền tảng dữ liệu và schema

  Task: Chuẩn hóa DataLoader và repository
  Goal: Nạp đúng CSV Olist, parse timestamp và tạo các truy vấn theo quyền truy cập agent.
  Files: services/data_loader.py, services/repository.py, config.py
  Minimal change: Ánh xạ đúng tên file, cache DataFrame, thêm truy vấn order/customer/items/payments/products/sellers.
  Verify command: pytest tests/test_repository.py -q
  Expected output: Tất cả truy vấn trả đúng dữ liệu cho EC_001.

  Task: Định nghĩa schema input và output
  Goal: Biểu diễn toàn bộ contract JSON và giới hạn rubric bằng Pydantic.
  Files: models/input_schema.py, models/output_schema.py
  Minimal change: Tạo nested models, enum, nullable field và max_length theo README.
  Verify command: pytest tests/test_schemas.py -q
  Expected output: Input mẫu validate; output hợp lệ serialize thành JSON.

  ### 2. Agent phân tích domain

  Task: Triển khai Customer và Order/Product agent
  Goal: Tạo customer context, affected entities và product context đúng quyền dữ liệu.
  Files: agents/customer_agent.py, agents/order_agent.py, services/repository.py
  Minimal change: Truy vấn customer history, items, sellers, products và category theo thứ tự nguồn.
  Verify command: pytest tests/test_customer_order_agents.py -q
  Expected output: Handoff đúng ID, không đưa history vào affected entities.

  Task: Triển khai Payment và Delivery agent
  Goal: Tính reconciliation và variance chính xác, xử lý dữ liệu thiếu.
  Files: agents/payment_agent.py, agents/delivery_agent.py, services/calculator.py
  Minimal change: Tính total/difference với làm tròn 2 số và trạng thái null theo R4.
  Verify command: pytest tests/test_payment_delivery_agents.py -q
  Expected output: Các công thức README và cờ seller late handoff đều pass.

  ### 3. Policy, evidence và verification

  Task: Triển khai Policy Agent
  Goal: Chuyển handoff domain thành kết luận EC_POLICY_V2 xác định.
  Files: agents/policy_agent.py, services/evidence.py
  Minimal change: Áp dụng primary issue theo ưu tiên, secondary issue/action theo thứ tự, refund và evidence hợp lệ.
  Verify command: pytest tests/test_policy_agent.py -q
  Expected output: Bao phủ toàn bộ primary issue và thứ tự action/evidence.

  Task: Triển khai Verifier Agent
  Goal: Chặn mọi output vi phạm schema hoặc rubric trước khi persist.
  Files: agents/verifier_agent.py, models/output_schema.py
  Minimal change: Kiểm tra ID tồn tại, refund, confidence, null semantics và giới hạn mảng.
  Verify command: pytest tests/test_verifier_agent.py -q
  Expected output: Output hợp lệ pass; fixture lỗi bị từ chối với thông báo cụ thể.

  ### 4. Orchestration, CLI và audit

  Task: Triển khai Coordinator
  Goal: Điều phối các agent đúng handoff sequence và tạo CaseOutput draft.
  Files: agents/coordinator.py, agents/*.py
  Minimal change: Khởi tạo dependency một lần, gọi agent theo R1, rồi gửi Verifier.
  Verify command: pytest tests/test_coordinator.py -q
  Expected output: Một case hoàn tất với JSON đã verify.

  Task: Triển khai CLI, output và audit
  Goal: Chạy single/batch case, ghi output, trace và metadata đúng yêu cầu nộp bài.
  Files: main.py, config.py, logging/trace.jsonl, logging/metadata.json
  Minimal change: Thêm argparse, tạo mới trace mỗi batch, ghi metadata model/runtime và tạo thư mục output nếu thiếu.
  Verify command: python main.py --all
  Expected output: Có 50 JSON hợp lệ, trace của lần chạy hiện tại và metadata.

  ### 5. Kiểm thử nghiệm thu

  Task: Thêm regression suite và kiểm tra batch
  Goal: Chứng minh pipeline thỏa R1–R6 trước khi nộp.
  Files: tests/, các fixture input tối thiểu
  ## Tiêu chí nghiệm thu

  - pytest -q pass.
  - Chạy batch tạo đúng 50 JSON, không có file lạ trong output/.
  - Mọi output parse lại được bởi CaseOutput.
  - Trace không append lịch sử cũ; metadata nêu model, parameter size, framework và runtime.
  - Không dùng LLM để suy diễn dữ liệu hoặc quyết định policy.

  ## Giả định

  - README.md là nguồn chuẩn cho EC_POLICY_V2 và output contract; architecture.md là nguồn chuẩn cho quyền truy cập/handoff.
  - Dự án là CLI Python nội bộ, không cần API web, queue hay thực thi song song.
  - Các thay đổi chưa commit trong services/data_loader.py và config.py được giữ nguyên để kiểm tra, không bị ghi đè ngoài phạm vi nhiệm vụ.
  - Artifact dự kiến: docs/plan/plan_add_feature_olist_dispute_resolution_20260805.md.