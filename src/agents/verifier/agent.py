"""Kiểm chứng output case trước khi ghi JSON."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence


TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
EVIDENCE_PATTERN = re.compile(r"^(order|item|payment|seller|policy):.+$")
ROOT_CAUSES = {
    "SELLER_HANDOFF_AFTER_LIMIT",
    "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT",
    "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED",
    "DELIVERY_WITHIN_ESTIMATE",
}
PRIMARY_ACTIONS = {
    "canceled_order_paid": "issue_full_refund",
    "unavailable_order_paid": "issue_full_refund",
    "late_delivery_seller": "refund_freight",
    "late_delivery_logistics": "refund_freight",
    "valid_split_payment": "explain_valid_split_payment",
    "unsupported_late_claim": "reject_late_refund",
}


@dataclass(frozen=True)
class VerificationResult:
    """Kết quả kiểm chứng để Coordinator quyết định có được ghi output hay không."""

    is_valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VerifierAgent:
    """Kiểm tra contract output được mô tả trong README."""

    _TOP_LEVEL_FIELDS = {
        "case_id",
        "case_assessment",
        "affected_entities",
        "customer_context",
        "product_context",
        "delivery_analysis",
        "payment_reconciliation",
        "root_cause_analysis",
        "evidence_ids",
        "financial_resolution",
        "resolution_actions",
    }
    _ARRAY_LIMITS = {
        ("affected_entities", "order_ids"): 5,
        ("affected_entities", "item_ids"): 5,
        ("affected_entities", "seller_ids"): 3,
        ("affected_entities", "payment_ids"): 5,
        ("customer_context", "related_order_ids"): 5,
        ("product_context", "product_ids"): 5,
        ("product_context", "category_names"): 5,
        ("root_cause_analysis", "ranked_causes"): 3,
        ("root_cause_analysis", "responsible_parties"): 3,
        ("", "evidence_ids"): 20,
        ("", "resolution_actions"): 5,
    }

    def verify(self, candidate: Mapping[str, Any]) -> VerificationResult:
        """Trả về tất cả lỗi phát hiện được; không sửa hoặc tự suy diễn output."""
        errors: list[str] = []
        self._check_top_level_fields(candidate, errors)
        if errors:
            return VerificationResult(is_valid=False, errors=errors)

        self._check_array_limits(candidate, errors)
        self._check_assessment(candidate, errors)
        self._check_timestamps(candidate, errors)
        self._check_financials(candidate, errors)
        self._check_root_causes(candidate, errors)
        self._check_actions_and_status(candidate, errors)
        self._check_evidence(candidate, errors)
        return VerificationResult(is_valid=not errors, errors=errors)

    def _check_top_level_fields(
        self, candidate: Mapping[str, Any], errors: list[str]
    ) -> None:
        missing = self._TOP_LEVEL_FIELDS - set(candidate)
        if missing:
            errors.append(f"Thiếu trường top-level: {', '.join(sorted(missing))}")
        for field in self._TOP_LEVEL_FIELDS - {"case_id", "evidence_ids", "resolution_actions"}:
            if field in candidate and not isinstance(candidate[field], Mapping):
                errors.append(f"{field} phải là object")

    def _check_array_limits(self, candidate: Mapping[str, Any], errors: list[str]) -> None:
        for (section, field), limit in self._ARRAY_LIMITS.items():
            container = candidate if not section else candidate.get(section, {})
            value = container.get(field) if isinstance(container, Mapping) else None
            if not isinstance(value, list):
                errors.append(f"{section + '.' if section else ''}{field} phải là array")
            elif len(value) > limit:
                errors.append(
                    f"{section + '.' if section else ''}{field} vượt giới hạn {limit}"
                )
            elif len(value) != len(set(map(str, value))):
                errors.append(f"{section + '.' if section else ''}{field} không được trùng lặp")

    @staticmethod
    def _check_assessment(candidate: Mapping[str, Any], errors: list[str]) -> None:
        assessment = candidate["case_assessment"]
        confidence = assessment.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            errors.append("case_assessment.confidence phải nằm trong [0, 1]")
        if assessment.get("case_status") not in {"action_required", "no_action"}:
            errors.append("case_assessment.case_status không hợp lệ")

    @staticmethod
    def _check_timestamps(candidate: Mapping[str, Any], errors: list[str]) -> None:
        delivery = candidate["delivery_analysis"]
        for field in ("delivered_at", "estimated_delivery_at", "carrier_handoff_at"):
            value = delivery.get(field)
            if value is not None and (not isinstance(value, str) or not TIMESTAMP_PATTERN.match(value)):
                errors.append(f"delivery_analysis.{field} phải là timestamp hoặc null")

    @staticmethod
    def _check_financials(candidate: Mapping[str, Any], errors: list[str]) -> None:
        payment = candidate["payment_reconciliation"]
        item_total = payment.get("item_total_brl")
        freight_total = payment.get("freight_total_brl")
        expected_total = payment.get("expected_total_brl")
        payment_total = payment.get("payment_total_brl")
        difference = payment.get("difference_brl")
        reconciled = payment.get("reconciled")

        if payment.get("currency") != "BRL":
            errors.append("payment_reconciliation.currency phải là BRL")
        financial = candidate["financial_resolution"]
        if financial.get("currency") != "BRL":
            errors.append("financial_resolution.currency phải là BRL")
        if any(value is None for value in (item_total, freight_total, expected_total, difference, reconciled)):
            if not all(value is None for value in (item_total, freight_total, expected_total, difference, reconciled)):
                errors.append("Nhóm trường payment null phải cùng null khi order không có item")
            return
        if not all(isinstance(value, (int, float)) for value in (item_total, freight_total, expected_total, payment_total, difference)):
            errors.append("Các tổng tiền payment phải là số")
            return
        expected = Decimal(str(item_total)) + Decimal(str(freight_total))
        actual_difference = Decimal(str(payment_total)) - Decimal(str(expected_total))
        if abs(expected - Decimal(str(expected_total))) > Decimal("0.01"):
            errors.append("expected_total_brl không bằng item_total_brl + freight_total_brl")
        if abs(actual_difference - Decimal(str(difference))) > Decimal("0.01"):
            errors.append("difference_brl không bằng payment_total_brl - expected_total_brl")
        for value in (item_total, freight_total, expected_total, payment_total, difference):
            if -Decimal(str(value)).as_tuple().exponent > 2:
                errors.append("Các tổng tiền payment chỉ được có tối đa 2 chữ số thập phân")
                break

    @staticmethod
    def _check_root_causes(candidate: Mapping[str, Any], errors: list[str]) -> None:
        ranked_causes = candidate["root_cause_analysis"].get("ranked_causes", [])
        for cause in ranked_causes:
            if cause.get("cause_code") not in ROOT_CAUSES:
                errors.append("root_cause_analysis có cause_code không hợp lệ")
            if not isinstance(cause.get("rank"), int) or cause["rank"] < 1:
                errors.append("root_cause_analysis.rank phải là số nguyên dương")

    @staticmethod
    def _check_actions_and_status(candidate: Mapping[str, Any], errors: list[str]) -> None:
        assessment = candidate["case_assessment"]
        primary_issue = assessment.get("primary_issue")
        actions = candidate["resolution_actions"]
        expected_action = PRIMARY_ACTIONS.get(primary_issue)
        if expected_action is None:
            errors.append("case_assessment.primary_issue không hợp lệ")
        elif not actions or actions[0] != expected_action:
            errors.append("resolution_actions phải bắt đầu bằng action chính của primary issue")

        refund = candidate["financial_resolution"].get("recommended_refund_brl")
        if not isinstance(refund, (int, float)) or refund < 0:
            errors.append("recommended_refund_brl phải là số không âm")
        elif (refund > 0) != (assessment.get("case_status") == "action_required"):
            errors.append("case_status phải khớp với recommended_refund_brl")

    @staticmethod
    def _check_evidence(candidate: Mapping[str, Any], errors: list[str]) -> None:
        evidence_ids = candidate["evidence_ids"]
        if not all(isinstance(value, str) and EVIDENCE_PATTERN.match(value) for value in evidence_ids):
            errors.append("evidence_ids có định dạng không hợp lệ")
            return

        affected = candidate["affected_entities"]
        valid_ids = {
            *(f"order:{value}" for value in affected.get("order_ids", [])),
            *(f"item:{value}" for value in affected.get("item_ids", [])),
            *(f"payment:{value}" for value in affected.get("payment_ids", [])),
            *(f"seller:{value}" for value in affected.get("seller_ids", [])),
        }
        ranked_causes = candidate["root_cause_analysis"].get("ranked_causes", [])
        valid_ids.update(f"policy:{cause['cause_code']}" for cause in ranked_causes)
        extras = set(evidence_ids) - valid_ids
        if extras:
            errors.append(f"evidence_ids không tham chiếu entity/policy hợp lệ: {sorted(extras)}")

        required = {
            *(f"order:{value}" for value in affected.get("order_ids", [])),
            *(f"item:{value}" for value in affected.get("item_ids", [])),
            *(f"payment:{value}" for value in affected.get("payment_ids", [])),
            *(f"policy:{cause['cause_code']}" for cause in ranked_causes),
        }
        responsible_sellers = [
            party.get("party_id")
            for party in candidate["root_cause_analysis"].get("responsible_parties", [])
            if party.get("party_type") == "seller"
        ]
        required.update(f"seller:{seller_id}" for seller_id in responsible_sellers)
        missing = required - set(evidence_ids)
        if missing:
            errors.append(f"evidence_ids thiếu evidence bắt buộc: {sorted(missing)}")
