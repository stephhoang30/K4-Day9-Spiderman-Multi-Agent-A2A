"""AgentState LangGraph. `trace` dùng reducer operator.add vì Customer Agent và
Order&Product Agent chạy song song, mỗi node đều append vào cùng key này —
không có reducer thì node chạy sau sẽ ghi đè mất entry của node chạy trước.
"""

import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict, total=False):
    case_input: dict
    order_id: str
    customer_result: dict
    order_product_result: dict
    payment_result: dict
    delivery_result: dict
    policy_result: dict
    verifier_result: dict
    trace: Annotated[list[dict], operator.add]
