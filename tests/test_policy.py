"""Regression test cho các primary issue của EC_POLICY_V2."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.customer import CustomerHandoff
from agents.delivery import DeliveryHandoff
from agents.payment import PaymentHandoff
from agents.policy import PolicyAgent


class PolicyAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = PolicyAgent()
        self.order = {"order_status": "delivered"}
        self.items = [{"item_id": "order:1"}]
        self.customer = CustomerHandoff("customer", [], 0, False)

    @staticmethod
    def payment(
        *, total: float = 120.0, freight: float | None = 20.0, count: int = 1,
        reconciled: bool | None = True,
    ) -> PaymentHandoff:
        return PaymentHandoff(
            "BRL", [f"order:{index}" for index in range(1, count + 1)], count,
            ["credit_card"], count >= 2, 100.0 if freight is not None else None,
            freight, 120.0 if freight is not None else None, total,
            0.0 if freight is not None else None, reconciled,
        )

    @staticmethod
    def delivery(
        *, late: bool = False, late_sellers: list[str] | None = None,
        carrier_handoff_at: str | None = "2018-01-01 12:00:00",
    ) -> DeliveryHandoff:
        return DeliveryHandoff(
            "2018-01-02 12:00:00", "2018-01-01 12:00:00", carrier_handoff_at,
            24.0 if late else -24.0, late, [], late_sellers or [],
        )

    def investigate(self, payment: PaymentHandoff, delivery: DeliveryHandoff):
        return self.agent.investigate(
            self.order, self.items, ["seller"], ["category"], self.customer,
            payment, delivery,
        )

    def test_canceled_paid_has_highest_priority(self) -> None:
        self.order["order_status"] = "canceled"
        result = self.investigate(self.payment(total=99.5), self.delivery(late=True, late_sellers=["seller"]))
        self.assertEqual(result.primary_issue, "canceled_order_paid")
        self.assertEqual(result.recommended_refund_brl, 99.5)
        self.assertEqual(result.resolution_actions[:2], ["issue_full_refund", "verify_refund_completion"])

    def test_unavailable_paid(self) -> None:
        self.order["order_status"] = "unavailable"
        result = self.investigate(self.payment(total=80.0), self.delivery())
        self.assertEqual(result.primary_issue, "unavailable_order_paid")

    def test_late_seller_refunds_freight(self) -> None:
        result = self.investigate(self.payment(freight=16.7), self.delivery(late=True, late_sellers=["seller"]))
        self.assertEqual(result.primary_issue, "late_delivery_seller")
        self.assertEqual(result.recommended_refund_brl, 16.7)
        self.assertIn("review_seller_handoff", result.resolution_actions)

    def test_late_logistics_refunds_freight(self) -> None:
        result = self.investigate(self.payment(freight=16.7), self.delivery(late=True))
        self.assertEqual(result.primary_issue, "late_delivery_logistics")
        self.assertEqual(result.responsible_parties[0]["party_id"], "LOGISTICS_PROVIDER")

    def test_valid_split_payment(self) -> None:
        result = self.investigate(self.payment(count=2), self.delivery())
        self.assertEqual(result.primary_issue, "valid_split_payment")
        self.assertNotIn("verify_payment_allocation", result.resolution_actions)

    def test_unsupported_late_claim(self) -> None:
        result = self.investigate(self.payment(), self.delivery())
        self.assertEqual(result.primary_issue, "unsupported_late_claim")

    def test_late_order_without_carrier_evidence_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "carrier_handoff_at"):
            self.investigate(self.payment(), self.delivery(late=True, carrier_handoff_at=None))


if __name__ == "__main__":
    unittest.main()
