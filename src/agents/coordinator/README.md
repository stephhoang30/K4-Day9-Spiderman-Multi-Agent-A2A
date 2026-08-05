# Agent điều phối

Nhận một case, phân công tác vụ theo domain và tổng hợp kết quả cuối cùng.

## Luồng điều phối

`CoordinatorAgent(data_dir).investigate(case)` gọi theo thứ tự:

1. Order & Product Agent
2. Customer, Payment và Delivery Agent
3. Policy Agent
4. Verifier Agent

Coordinator dựng JSON đúng output schema, giới hạn các array theo README và chỉ trả kết quả khi Verifier Agent xác nhận hợp lệ. Việc đọc/ghi file case batch và trace thuộc `orchestration/`, không nằm trong agent này.
