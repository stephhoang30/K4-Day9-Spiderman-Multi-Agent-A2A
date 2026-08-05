"""Truy xuất dữ liệu đơn hàng và sản phẩm cho một case Olist.

Module chỉ bàn giao các trường cần cho Customer, Payment, Delivery và Policy;
không chuyển nguyên record CSV giữa các agent.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OrderProductHandoff:
    """Contract bàn giao của Order & Product Agent."""

    order: dict[str, str | None]
    items: list[dict[str, Any]]
    seller_ids: list[str]
    product_ids: list[str]
    category_names: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Chuyển handoff thành kiểu dữ liệu có thể ghi JSON."""
        return asdict(self)


class OrderProductAgent:
    """Đọc CSV Olist một lần và trả về ngữ cảnh order/product theo order ID."""

    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = Path(data_dir)
        self._orders = self._index_orders()
        self._items_by_order = self._index_items()
        self._products = self._index_by_key(
            "olist_products_dataset.csv", "product_id"
        )

    def investigate(self, order_id: str) -> OrderProductHandoff:
        """Trả về order, item, seller, product và category của một order.

        Raises:
            KeyError: Nếu `order_id` không tồn tại trong bảng orders.
        """
        if order_id not in self._orders:
            raise KeyError(f"Không tìm thấy order_id trong dữ liệu Olist: {order_id}")

        items: list[dict[str, Any]] = []
        seller_ids: list[str] = []
        product_ids: list[str] = []
        category_names: list[str] = []

        for item in self._items_by_order.get(order_id, []):
            product = self._products.get(item["product_id"], {})
            seller_id = item["seller_id"]
            category_name = product.get("product_category_name") or None
            item_context = {
                "item_id": f"{order_id}:{item['order_item_id']}",
                "order_item_id": item["order_item_id"],
                "product_id": item["product_id"],
                "seller_id": seller_id,
                "shipping_limit_date": item["shipping_limit_date"] or None,
                "price": item["price"],
                "freight_value": item["freight_value"],
                "category_name": category_name,
            }
            items.append(item_context)
            self._append_once(seller_ids, seller_id)
            self._append_once(product_ids, item["product_id"])
            if category_name:
                self._append_once(category_names, category_name)

        return OrderProductHandoff(
            order=self._build_order_context(self._orders[order_id]),
            items=items,
            seller_ids=seller_ids,
            product_ids=product_ids,
            category_names=category_names,
        )

    def _index_orders(self) -> dict[str, dict[str, str | None]]:
        return self._index_by_key("olist_orders_dataset.csv", "order_id")

    @staticmethod
    def _build_order_context(order: dict[str, str | None]) -> dict[str, str | None]:
        """Chọn đúng trường order mà các agent tiếp theo cần dùng."""
        fields = (
            "order_id",
            "customer_id",
            "order_status",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        )
        return {field: order[field] for field in fields}

    def _index_items(self) -> dict[str, list[dict[str, str]]]:
        result: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in self._read_csv("olist_order_items_dataset.csv"):
            result[row["order_id"]].append(row)
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
        # Một số CSV Olist có UTF-8 BOM ở header; utf-8-sig loại bỏ BOM an toàn.
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    @staticmethod
    def _append_once(values: list[str], value: str) -> None:
        if value not in values:
            values.append(value)
