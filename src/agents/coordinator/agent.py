"""Điều phối pipeline multi-agent cho một case khiếu nại Olist."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Callable
from typing import Any, Mapping

from agents.customer import CustomerAgent
from agents.delivery import DeliveryAgent
from agents.order_product import OrderProductAgent
from agents.payment import PaymentAgent
from agents.policy import PolicyAgent
from agents.verifier import VerifierAgent


class CoordinatorAgent:
    """Tổng hợp handoff domain thành output schema của README."""

    def __init__(self, data_dir: str | Path) -> None:
        self._order_product = OrderProductAgent(data_dir)
        self._customer = CustomerAgent(data_dir)
        self._payment = PaymentAgent(data_dir)
        self._delivery = DeliveryAgent()
        self._policy = PolicyAgent()
        self._verifier = VerifierAgent()

    def investigate(
        self,
        case: Mapping[str, Any],
        on_handoff: Callable[[str, Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Điều tra một case và trả JSON đã qua Verifier Agent.

        Raises:
            KeyError: Nếu case không có case_id hoặc claimed_order_id.
            ValueError: Nếu policy hoặc verifier không thể chấp nhận output.
        """
        case_id = str(case["case_id"])
        order_id = str(case["customer_request"]["claimed_order_id"])

        order_product = self._order_product.investigate(order_id)
        self._emit(on_handoff, "order_product", {
            "order_id": order_id,
            "item_count": len(order_product.items),
            "seller_count": len(order_product.seller_ids),
            "product_count": len(order_product.product_ids),
        })
        customer = self._customer.investigate(order_product.order["customer_id"] or "", order_id)
        self._emit(on_handoff, "customer", customer.to_dict())
        payment = self._payment.investigate(order_id, order_product.items)
        self._emit(on_handoff, "payment", payment.to_dict())
        delivery = self._delivery.investigate(order_product.order, order_product.items)
        self._emit(on_handoff, "delivery", delivery.to_dict())
        policy = self._policy.investigate(
            order_product.order,
            order_product.items,
            order_product.seller_ids,
            order_product.category_names,
            customer,
            payment,
            delivery,
        )
        self._emit(on_handoff, "policy", policy.to_dict())

        candidate = self._build_output(
            case_id, order_id, order_product, customer, payment, delivery, policy
        )
        verification = self._verifier.verify(candidate)
        self._emit(on_handoff, "verifier", verification.to_dict())
        if not verification.is_valid:
            raise ValueError("Output không qua Verifier Agent: " + "; ".join(verification.errors))
        return candidate

    @staticmethod
    def _emit(
        on_handoff: Callable[[str, Mapping[str, Any]], None] | None,
        agent_name: str,
        handoff: Mapping[str, Any],
    ) -> None:
        if on_handoff is not None:
            on_handoff(agent_name, handoff)

    @staticmethod
    def _build_output(
        case_id: str,
        order_id: str,
        order_product: Any,
        customer: Any,
        payment: Any,
        delivery: Any,
        policy: Any,
    ) -> dict[str, Any]:
        seller_ids = order_product.seller_ids[:3]
        item_ids = [item["item_id"] for item in order_product.items[:5]]
        payment_ids = payment.payment_ids[:5]
        responsible_seller_ids = [
            party["party_id"]
            for party in policy.responsible_parties
            if party["party_type"] == "seller"
        ]
        root_cause = {"cause_code": policy.root_cause_code, "rank": 1}

        evidence_ids = [
            f"order:{order_id}",
            *(f"item:{item_id}" for item_id in item_ids),
            *(f"payment:{payment_id}" for payment_id in payment_ids),
            *(f"seller:{seller_id}" for seller_id in responsible_seller_ids),
            f"policy:{policy.root_cause_code}",
        ]
        return {
            "case_id": case_id,
            "case_assessment": {
                "primary_issue": policy.primary_issue,
                "secondary_issues": policy.secondary_issues,
                "case_status": policy.case_status,
                "confidence": 1.0,
            },
            "affected_entities": {
                "order_ids": [order_id],
                "item_ids": item_ids,
                "seller_ids": seller_ids,
                "payment_ids": payment_ids,
            },
            "customer_context": {
                "customer_unique_id": customer.customer_unique_id,
                "related_order_ids": customer.related_order_ids,
            },
            "product_context": {
                "product_ids": order_product.product_ids[:5],
                "category_names": order_product.category_names[:5],
            },
            "delivery_analysis": {
                "delivered_at": delivery.delivered_at,
                "estimated_delivery_at": delivery.estimated_delivery_at,
                "carrier_handoff_at": delivery.carrier_handoff_at,
                "delivery_variance_hours": delivery.delivery_variance_hours,
                "seller_handoff_analysis": delivery.seller_handoff_analysis,
                "late_handoff_seller_ids": delivery.late_handoff_seller_ids[:3],
            },
            "payment_reconciliation": {
                "currency": payment.currency,
                "item_total_brl": payment.item_total_brl,
                "freight_total_brl": payment.freight_total_brl,
                "expected_total_brl": payment.expected_total_brl,
                "payment_total_brl": payment.payment_total_brl,
                "difference_brl": payment.difference_brl,
                "reconciled": payment.reconciled,
                "payment_types": payment.payment_types,
            },
            "root_cause_analysis": {
                "ranked_causes": [root_cause],
                "responsible_parties": policy.responsible_parties,
            },
            "evidence_ids": evidence_ids,
            "financial_resolution": {
                "currency": "BRL",
                "recommended_refund_brl": policy.recommended_refund_brl,
            },
            "resolution_actions": policy.resolution_actions,
        }
