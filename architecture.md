# Architecture Diagram

This repository implements a Multi-Agent architecture for E-commerce Dispute Resolution.

## Agents & Roles

1. **Coordinator Agent (`coordinator.py`)**: 
   - Receives the case and orchestrates the child agents.
   - Computes secondary issues and structures all output accurately based on the case schemas.
   - Enforces specific validation orders for resolution actions.
2. **Customer Agent (`customer_agent.py`)**: 
   - Resolves the specific `customer_id` strictly using the `customer_unique_id`.
   - Reconstructs the timeline and fetches related historical `order_id`s.
3. **Order Agent (`order_agent.py`)**: 
   - Retrieves primary order data, line items, and responsible sellers.
4. **Payment Agent (`payment_agent.py`)**: 
   - Analyzes payment rows, sums total payment values, calculates expected total derived from item price + freight, and flags variance discrepancies.
5. **Delivery Agent (`delivery_agent.py`)**: 
   - Evaluates overall delivery variance against estimated dates.
   - Tracks seller handoff variance at granular item levels to determine exact delays against `shipping_limit_date`.
6. **Policy Agent (`policy_agent.py`)**: 
   - Acts as the core rule engine encapsulating `EC_POLICY_V2`.
   - Examines conditions (order cancellation, late delivery, reconciliation logic) to finalize actions, responsible parties, strict root causes, and financial refund amounts.
7. **Verifier Agent (`verifier_agent.py`)**: 
   - Ensures strict JSON schematics compliance and maximum array element limiting before finalizing case outputs.

## Data Flow
- `Case Input` -> `Coordinator` -> dispatches to `Domain Agents (Customer, Order, Payment, Delivery)` sequentially (or pseudo-concurrently) via structured JSON payload.
- Domain Contexts -> `Policy Agent` -> determines primary and secondary actions and monetary values.
- Evaluated Structure -> `Coordinator` -> packages objects based on Pydantic output schemas from `output_schema.py`.
- Formatted Output -> `Verifier Agent` -> tests format correctness -> `Stored to File / trace.jsonl`.
