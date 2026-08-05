# Agent chính sách

Áp dụng `EC_POLICY_V2` để xác định vấn đề, trách nhiệm, khoản hoàn và hành động xử lý.

## Contract bàn giao

`PolicyAgent().investigate(...)` nhận handoff của Order & Product, Customer, Payment và Delivery Agent. Agent trả:

- `primary_issue`, `secondary_issues`, `case_status`;
- `root_cause_code`, `responsible_parties`;
- `recommended_refund_brl`, `resolution_actions`.

Primary issue được chọn theo đúng thứ tự ưu tiên trong README. Secondary issues và action bổ sung giữ đúng thứ tự nghiệp vụ. Nếu dữ liệu không thỏa rule nào của `EC_POLICY_V2`, agent báo lỗi thay vì tự suy diễn kết luận.
