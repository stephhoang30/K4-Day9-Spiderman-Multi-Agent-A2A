"""Truy xuất định danh khách hàng và lịch sử đơn hàng liên quan."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CustomerHandoff:
    """Contract bàn giao của Customer Agent."""

    customer_unique_id: str
    related_order_ids: list[str]
    related_order_count: int
    is_repeat_customer: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CustomerAgent:
    """Tìm customer_unique_id và các order khác của cùng một khách hàng."""

    MAX_RELATED_ORDER_IDS = 5

    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = Path(data_dir)
        self._customers = self._index_by_key("olist_customers_dataset.csv", "customer_id")
        self._orders_by_customer_unique_id = self._index_orders_by_customer_unique_id()

    def investigate(self, customer_id: str, claimed_order_id: str) -> CustomerHandoff:
        """Bàn giao lịch sử của khách, không đưa chính order đang điều tra vào lịch sử.

        Raises:
            KeyError: Nếu customer không tồn tại hoặc order không thuộc customer này.
        """
        customer = self._customers.get(customer_id)
        if customer is None:
            raise KeyError(f"Không tìm thấy customer_id trong dữ liệu Olist: {customer_id}")

        customer_unique_id = customer["customer_unique_id"]
        assert customer_unique_id is not None
        order_ids = self._orders_by_customer_unique_id[customer_unique_id]
        if claimed_order_id not in order_ids:
            raise KeyError(
                "claimed_order_id không thuộc customer_id đang được bàn giao: "
                f"{claimed_order_id}"
            )

        related_order_ids = [
            order_id for order_id in order_ids if order_id != claimed_order_id
        ]
        return CustomerHandoff(
            customer_unique_id=customer_unique_id,
            related_order_ids=related_order_ids[: self.MAX_RELATED_ORDER_IDS],
            related_order_count=len(related_order_ids),
            is_repeat_customer=bool(related_order_ids),
        )

    def _index_orders_by_customer_unique_id(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = defaultdict(list)
        for order in self._read_csv("olist_orders_dataset.csv"):
            customer = self._customers.get(order["customer_id"])
            if customer is None or customer["customer_unique_id"] is None:
                continue
            result[customer["customer_unique_id"]].append(order["order_id"])
        return dict(result)

    def _index_by_key(
        self, filename: str, key: str
    ) -> dict[str, dict[str, str | None]]:
        return {
            row[key]: {column: value or None for column, value in row.items()}
            for row in self._read_csv(filename)
        }

    def _read_csv(self, filename: str) -> list[dict[str, str]]:
        path = self._data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))
