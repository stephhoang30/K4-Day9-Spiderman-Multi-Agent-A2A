"""Đối soát thanh toán với giá item và phí vận chuyển."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Mapping, Sequence


MONEY_QUANTUM = Decimal("0.01")
RECONCILIATION_TOLERANCE = Decimal("0.10")


@dataclass(frozen=True)
class PaymentHandoff:
    """Contract bàn giao của Payment Agent."""

    currency: str
    payment_ids: list[str]
    payment_count: int
    payment_types: list[str]
    is_split_payment: bool
    item_total_brl: float | None
    freight_total_brl: float | None
    expected_total_brl: float | None
    payment_total_brl: float
    difference_brl: float | None
    reconciled: bool | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PaymentAgent:
    """Đọc payment rows và tính kết quả đối soát theo policy EC_POLICY_V2."""

    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = Path(data_dir)
        self._payments_by_order = self._index_payments()

    def investigate(
        self, order_id: str, items: Sequence[Mapping[str, Any]]
    ) -> PaymentHandoff:
        """Đối soát payment với các item mà Order & Product Agent đã bàn giao."""
        payments = self._payments_by_order.get(order_id, [])
        payment_total = sum(
            (Decimal(payment["payment_value"]) for payment in payments), Decimal("0")
        )
        payment_types: list[str] = []
        for payment in payments:
            self._append_once(payment_types, payment["payment_type"])

        if not items:
            return PaymentHandoff(
                currency="BRL",
                payment_ids=self._payment_ids(order_id, payments),
                payment_count=len(payments),
                payment_types=payment_types,
                is_split_payment=len(payments) >= 2,
                item_total_brl=None,
                freight_total_brl=None,
                expected_total_brl=None,
                payment_total_brl=self._as_brl(payment_total),
                difference_brl=None,
                reconciled=None,
            )

        item_total = sum((Decimal(str(item["price"])) for item in items), Decimal("0"))
        freight_total = sum(
            (Decimal(str(item["freight_value"])) for item in items), Decimal("0")
        )
        expected_total = item_total + freight_total
        difference = payment_total - expected_total

        return PaymentHandoff(
            currency="BRL",
            payment_ids=self._payment_ids(order_id, payments),
            payment_count=len(payments),
            payment_types=payment_types,
            is_split_payment=len(payments) >= 2,
            item_total_brl=self._as_brl(item_total),
            freight_total_brl=self._as_brl(freight_total),
            expected_total_brl=self._as_brl(expected_total),
            payment_total_brl=self._as_brl(payment_total),
            difference_brl=self._as_brl(difference),
            reconciled=abs(difference) <= RECONCILIATION_TOLERANCE,
        )

    def _index_payments(self) -> dict[str, list[dict[str, str]]]:
        result: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in self._read_csv("olist_order_payments_dataset.csv"):
            result[row["order_id"]].append(row)
        return dict(result)

    def _read_csv(self, filename: str) -> list[dict[str, str]]:
        path = self._data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    @staticmethod
    def _payment_ids(order_id: str, payments: Sequence[Mapping[str, str]]) -> list[str]:
        return [f"{order_id}:{payment['payment_sequential']}" for payment in payments]

    @staticmethod
    def _append_once(values: list[str], value: str) -> None:
        if value not in values:
            values.append(value)

    @staticmethod
    def _as_brl(value: Decimal) -> float:
        return float(value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP))
