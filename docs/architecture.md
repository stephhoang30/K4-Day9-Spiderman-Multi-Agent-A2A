# Multi-Agent Architecture

## Overall Workflow

```text
                +-------------------+
                |   Input (Case)    |
                +---------+---------+
                          |
                          v
                +-------------------+
                | Coordinator Agent |
                +---------+---------+
                          |
      +---------+---------+---------+---------+
      |         |         |         |         |
      v         v         v         v         v
+-----------+ +---------+ +---------+ +---------+ +---------+
| Customer  | | Order & | | Payment | |Delivery | | Policy  |
|  Agent    | | Product | |  Agent  | |  Agent  | |  Agent  |
+-----+-----+ +----+----+ +----+----+ +----+----+ +----+----+
      \            |            |            |           /
       \___________|____________|____________|__________/
                           |
                           v
                  +-----------------+
                  | Verifier Agent  |
                  +--------+--------+
                           |
                           v
                    Output JSON File
```

---

# Agent Responsibilities

## 1. Coordinator Agent
- Nhận input case.
- Điều phối các agent.
- Tổng hợp kết quả.
- Sinh output cuối.

### Access
- Input JSON
- Kết quả từ các agent

---

## 2. Customer Agent
### Responsibilities
- Tìm customer.
- Lấy customer history.
- Xác định related orders.

### Access
- customers.csv
- orders.csv

Output:
- customer_context

---

## 3. Order & Product Agent
### Responsibilities
- Phân tích order.
- Lấy items.
- Seller.
- Product.
- Category.

### Access
- orders.csv
- order_items.csv
- products.csv
- sellers.csv

Output:
- affected_entities
- product_context

---

## 4. Payment Agent

### Responsibilities
- Tổng payment.
- Payment types.
- Payment reconciliation.

### Access
- order_payments.csv
- order_items.csv

Output:
- payment_reconciliation

---

## 5. Delivery Agent

### Responsibilities
- Delivery variance.
- Seller handoff variance.
- Late seller.
- Late logistics.

### Access
- orders.csv
- order_items.csv

Output:
- delivery_analysis

---

## 6. Policy Agent

### Responsibilities
- Áp dụng EC_POLICY_V2.
- Xác định:
  - primary issue
  - secondary issues
  - responsible parties
  - refund
  - actions
  - evidence ids

### Access
- Outputs của tất cả agent
- EC_POLICY_V2

Output:
- case_assessment
- root_cause_analysis
- financial_resolution
- resolution_actions
- evidence_ids

---

## 7. Verifier Agent

### Responsibilities
- Validate schema.
- Validate IDs.
- Validate refund.
- Validate array limits.
- Validate null handling.
- Kiểm tra confidence.

Output:
- Final JSON

---

# Handoff

```
Coordinator
    ↓
Customer Agent
    ↓
Coordinator
    ↓
Order/Product Agent
    ↓
Coordinator
    ↓
Payment Agent
    ↓
Coordinator
    ↓
Delivery Agent
    ↓
Coordinator
    ↓
Policy Agent
    ↓
Coordinator
    ↓
Verifier Agent
    ↓
Output
```

---

# Data Access Matrix

| Agent | Data Access |
|--------|-------------|
| Customer | customers, orders |
| Order & Product | orders, order_items, products, sellers |
| Payment | order_items, order_payments |
| Delivery | orders, order_items |
| Policy | Outputs from all agents + EC_POLICY_V2 |
| Verifier | Final output |

---

# Design Principles

- Single responsibility for each agent.
- Coordinator only orchestrates, không xử lý nghiệp vụ.
- Mỗi agent chỉ đọc dữ liệu cần thiết.
- Policy chỉ sử dụng kết quả từ các agent khác.
- Verifier là bước cuối để đảm bảo output hợp lệ trước khi ghi file.