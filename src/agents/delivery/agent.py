"""Tính chênh lệch giao hàng và bàn giao của seller."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping, Sequence


HOUR_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class DeliveryHandoff:
    """Contract bàn giao của Delivery Agent."""

    delivered_at: str | None
    estimated_delivery_at: str | None
    carrier_handoff_at: str | None
    delivery_variance_hours: float | None
    is_late_delivery: bool
    seller_handoff_analysis: list[dict[str, str | float | bool | None]]
    late_handoff_seller_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DeliveryAgent:
    """Tạo delivery analysis theo công thức và thứ tự trong README."""

    def investigate(
        self, order: Mapping[str, str | None], items: Sequence[Mapping[str, Any]]
    ) -> DeliveryHandoff:
        """Phân tích delivery và seller handoff từ handoff Order & Product Agent."""
        delivered_at = order["order_delivered_customer_date"]
        estimated_at = order["order_estimated_delivery_date"]
        carrier_handoff_at = order["order_delivered_carrier_date"]
        delivery_variance = self._variance_hours(delivered_at, estimated_at)

        seller_limits = self._earliest_shipping_limit_by_seller(items)
        seller_handoff_analysis: list[dict[str, str | float | bool | None]] = []
        late_handoff_seller_ids: list[str] = []
        for seller_id, shipping_limit_at in seller_limits.items():
            handoff_variance = self._variance_hours(carrier_handoff_at, shipping_limit_at)
            late_handoff = handoff_variance is not None and handoff_variance > 0
            seller_handoff_analysis.append(
                {
                    "seller_id": seller_id,
                    "shipping_limit_at": shipping_limit_at,
                    "handoff_variance_hours": handoff_variance,
                    "late_handoff": late_handoff,
                }
            )
            if late_handoff:
                late_handoff_seller_ids.append(seller_id)

        return DeliveryHandoff(
            delivered_at=delivered_at,
            estimated_delivery_at=estimated_at,
            carrier_handoff_at=carrier_handoff_at,
            delivery_variance_hours=delivery_variance,
            is_late_delivery=delivery_variance is not None and delivery_variance > 0,
            seller_handoff_analysis=seller_handoff_analysis,
            late_handoff_seller_ids=late_handoff_seller_ids,
        )

    def _earliest_shipping_limit_by_seller(
        self, items: Sequence[Mapping[str, Any]]
    ) -> OrderedDict[str, str | None]:
        """Gộp item theo seller, giữ thứ tự xuất hiện và chọn limit sớm nhất."""
        seller_limits: OrderedDict[str, str | None] = OrderedDict()
        for item in items:
            seller_id = str(item["seller_id"])
            shipping_limit_at = item.get("shipping_limit_date")
            current_limit = seller_limits.get(seller_id)
            if seller_id not in seller_limits or self._is_earlier(
                shipping_limit_at, current_limit
            ):
                seller_limits[seller_id] = shipping_limit_at
        return seller_limits

    @staticmethod
    def _is_earlier(candidate: Any, current: str | None) -> bool:
        if candidate is None:
            return False
        if current is None:
            return True
        return DeliveryAgent._parse_timestamp(str(candidate)) < DeliveryAgent._parse_timestamp(
            current
        )

    @staticmethod
    def _variance_hours(later: str | None, earlier: str | None) -> float | None:
        if later is None or earlier is None:
            return None
        delta = DeliveryAgent._parse_timestamp(later) - DeliveryAgent._parse_timestamp(earlier)
        hours = Decimal(delta.total_seconds()) / Decimal(3600)
        return float(hours.quantize(HOUR_QUANTUM, rounding=ROUND_HALF_UP))

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
