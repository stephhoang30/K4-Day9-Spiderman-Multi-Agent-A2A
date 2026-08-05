"""Áp dụng quy tắc EC_POLICY_V2 trên các handoff đã được kiểm chứng."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from agents.customer import CustomerHandoff
from agents.delivery import DeliveryHandoff
from agents.payment import PaymentHandoff


@dataclass(frozen=True)
class PolicyHandoff:
    """Kết luận chính sách trước bước dựng JSON và kiểm chứng cuối."""

    primary_issue: str
    secondary_issues: list[str]
    case_status: str
    root_cause_code: str
    responsible_parties: list[dict[str, str]]
    recommended_refund_brl: float
    resolution_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PolicyAgent:
    """Áp dụng bảng quyết định và thứ tự secondary/action trong README."""

    def investigate(
        self,
        order: Mapping[str, str | None],
        items: Sequence[Mapping[str, Any]],
        seller_ids: Sequence[str],
        category_names: Sequence[str],
        customer: CustomerHandoff,
        payment: PaymentHandoff,
        delivery: DeliveryHandoff,
    ) -> PolicyHandoff:
        """Đưa ra quyết định duy nhất theo EC_POLICY_V2.

        Raises:
            ValueError: Nếu dữ liệu không thỏa bất kỳ rule nào trong README.
        """
        primary_issue, root_cause_code, responsible_parties, refund, main_action = (
            self._select_primary(order, payment, delivery)
        )
        secondary_issues = self._secondary_issues(
            items, seller_ids, category_names, customer, payment
        )
        actions = self._actions(
            primary_issue, secondary_issues, refund, delivery
        )
        return PolicyHandoff(
            primary_issue=primary_issue,
            secondary_issues=secondary_issues,
            case_status="action_required" if refund > 0 else "no_action",
            root_cause_code=root_cause_code,
            responsible_parties=responsible_parties,
            recommended_refund_brl=refund,
            resolution_actions=[main_action, *actions],
        )

    @staticmethod
    def _select_primary(
        order: Mapping[str, str | None],
        payment: PaymentHandoff,
        delivery: DeliveryHandoff,
    ) -> tuple[str, str, list[dict[str, str]], float, str]:
        status = order["order_status"]
        if status == "canceled" and payment.payment_total_brl > 0:
            return (
                "canceled_order_paid",
                "ORDER_CANCELED_AFTER_PAYMENT",
                [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}],
                payment.payment_total_brl,
                "issue_full_refund",
            )
        if status == "unavailable" and payment.payment_total_brl > 0:
            return (
                "unavailable_order_paid",
                "ORDER_UNAVAILABLE_AFTER_PAYMENT",
                [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}],
                payment.payment_total_brl,
                "issue_full_refund",
            )
        if delivery.is_late_delivery and delivery.late_handoff_seller_ids:
            return (
                "late_delivery_seller",
                "SELLER_HANDOFF_AFTER_LIMIT",
                [
                    {"party_type": "seller", "party_id": seller_id}
                    for seller_id in delivery.late_handoff_seller_ids[:3]
                ],
                payment.freight_total_brl or 0.0,
                "refund_freight",
            )
        if delivery.is_late_delivery and not delivery.late_handoff_seller_ids:
            return (
                "late_delivery_logistics",
                "CARRIER_DELIVERED_AFTER_ESTIMATE",
                [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}],
                payment.freight_total_brl or 0.0,
                "refund_freight",
            )
        if payment.is_split_payment and payment.reconciled is True:
            return (
                "valid_split_payment",
                "MULTIPLE_PAYMENTS_RECONCILED",
                [],
                0.0,
                "explain_valid_split_payment",
            )
        if (
            delivery.delivery_variance_hours is not None
            and delivery.delivery_variance_hours <= 0
            and payment.reconciled is True
        ):
            return (
                "unsupported_late_claim",
                "DELIVERY_WITHIN_ESTIMATE",
                [],
                0.0,
                "reject_late_refund",
            )
        raise ValueError("Dữ liệu case không thỏa rule nào của EC_POLICY_V2")

    @staticmethod
    def _secondary_issues(
        items: Sequence[Mapping[str, Any]],
        seller_ids: Sequence[str],
        category_names: Sequence[str],
        customer: CustomerHandoff,
        payment: PaymentHandoff,
    ) -> list[str]:
        issues: list[str] = []
        if len(items) >= 2:
            issues.append("multi_item_order")
        if len(seller_ids) >= 2:
            issues.append("multi_seller_order")
        if payment.is_split_payment:
            issues.append("split_payment")
        if customer.is_repeat_customer:
            issues.append("repeat_customer")
        if len(category_names) >= 2:
            issues.append("multiple_categories")
        return issues

    @staticmethod
    def _actions(
        primary_issue: str,
        secondary_issues: Sequence[str],
        refund: float,
        delivery: DeliveryHandoff,
    ) -> list[str]:
        actions: list[str] = []
        if primary_issue == "late_delivery_seller":
            actions.append("review_seller_handoff")
        elif primary_issue == "late_delivery_logistics":
            actions.append("review_carrier_delay")
        if refund > 0:
            actions.append("verify_refund_completion")
        if "multi_seller_order" in secondary_issues:
            actions.append("coordinate_multi_seller_case")
        if (
            "split_payment" in secondary_issues
            and primary_issue != "valid_split_payment"
        ):
            actions.append("verify_payment_allocation")
        return actions[:4]
