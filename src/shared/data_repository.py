"""Kho dữ liệu Olist chỉ đọc, được chia sẻ bởi các agent."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


class DataRepository:
    """Đọc mỗi bảng cần thiết đúng một lần và cung cấp index theo khóa join."""

    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = Path(data_dir)
        self.orders_by_id = self._index_by_key("olist_orders_dataset.csv", "order_id")
        self.customers_by_id = self._index_by_key(
            "olist_customers_dataset.csv", "customer_id"
        )
        self.items_by_order_id = self._index_by_order("olist_order_items_dataset.csv")
        self.payments_by_order_id = self._index_by_order(
            "olist_order_payments_dataset.csv"
        )
        self.products_by_id = self._index_by_key(
            "olist_products_dataset.csv", "product_id"
        )
        self.seller_ids = set(
            self._index_by_key("olist_sellers_dataset.csv", "seller_id")
        )
        self.order_ids_by_customer_unique_id = self._index_customer_orders()

    def _index_customer_orders(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = defaultdict(list)
        for order in self.orders_by_id.values():
            customer = self.customers_by_id.get(order["customer_id"] or "")
            if customer is not None and customer["customer_unique_id"] is not None:
                result[customer["customer_unique_id"]].append(order["order_id"] or "")
        return dict(result)

    def has_order(self, order_id: str) -> bool:
        return order_id in self.orders_by_id

    def has_item(self, order_id: str, order_item_id: str) -> bool:
        return any(
            item["order_item_id"] == order_item_id
            for item in self.items_by_order_id.get(order_id, [])
        )

    def has_payment(self, order_id: str, payment_sequential: str) -> bool:
        return any(
            payment["payment_sequential"] == payment_sequential
            for payment in self.payments_by_order_id.get(order_id, [])
        )

    def has_seller(self, seller_id: str) -> bool:
        return seller_id in self.seller_ids

    def _index_by_order(self, filename: str) -> dict[str, list[dict[str, str | None]]]:
        result: dict[str, list[dict[str, str | None]]] = defaultdict(list)
        for row in self._read_csv(filename):
            normalized = {column: value or None for column, value in row.items()}
            order_id = normalized["order_id"]
            assert order_id is not None
            result[order_id].append(normalized)
        return dict(result)

    def _index_by_key(
        self, filename: str, key: str
    ) -> dict[str, dict[str, str | None]]:
        result: dict[str, dict[str, str | None]] = {}
        for row in self._read_csv(filename):
            normalized = {column: value or None for column, value in row.items()}
            row_key = normalized[key]
            assert row_key is not None
            result[row_key] = normalized
        return result

    def _read_csv(self, filename: str) -> list[dict[str, str]]:
        path = self._data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))
