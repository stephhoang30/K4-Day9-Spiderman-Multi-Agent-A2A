"""Coordinator: build DAG LangGraph và chạy 1 case.

DAG (khớp architecture.md):
  START -> order_product_agent
  order_product_agent -> customer_agent, payment_agent, delivery_agent (song song)
  customer_agent, payment_agent, delivery_agent -> policy_agent
  policy_agent -> verifier_agent -> END

customer_agent không đọc order_product_result (độc lập dữ liệu) nhưng vẫn đặt
sau order_product_agent thay vì thẳng từ START: LangGraph AND-join tại
policy_agent yêu cầu các nhánh hội tụ cùng "độ sâu" (số superstep) kể từ START,
nếu không nhánh ngắn hơn (customer_agent) sẽ kích hoạt policy_agent sớm trước khi
payment_agent/delivery_agent (2 hop) kịp chạy, gây KeyError khi đọc state.
"""

from langgraph.graph import END, START, StateGraph

from agents import customer_agent, delivery_agent, order_product_agent, payment_agent, policy_agent, verifier_agent
from agents.state import AgentState

_graph = None


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("customer_agent", customer_agent.run)
    graph.add_node("order_product_agent", order_product_agent.run)
    graph.add_node("payment_agent", payment_agent.run)
    graph.add_node("delivery_agent", delivery_agent.run)
    graph.add_node("policy_agent", policy_agent.run)
    graph.add_node("verifier_agent", verifier_agent.run)

    graph.add_edge(START, "order_product_agent")
    graph.add_edge("order_product_agent", "customer_agent")
    graph.add_edge("order_product_agent", "payment_agent")
    graph.add_edge("order_product_agent", "delivery_agent")
    graph.add_edge("customer_agent", "policy_agent")
    graph.add_edge("payment_agent", "policy_agent")
    graph.add_edge("delivery_agent", "policy_agent")
    graph.add_edge("policy_agent", "verifier_agent")
    graph.add_edge("verifier_agent", END)

    return graph.compile()


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_case(case_input: dict) -> dict:
    order_id = case_input["customer_request"]["claimed_order_id"]
    initial_state: AgentState = {
        "case_input": case_input,
        "order_id": order_id,
        "trace": [],
    }
    return get_graph().invoke(initial_state)
