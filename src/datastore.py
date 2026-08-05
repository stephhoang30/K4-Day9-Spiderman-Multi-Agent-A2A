"""Data layer: index 9 file CSV Olist mot lan, moi agent tra cuu O(1).

Khong tinh toan gi o day. Khong lam tron. Khong parse datetime.
Moi phep tinh nam o src/tools.py.
"""
from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict

from src import variants

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

INDEXES = {
    "orders": "order_id -> dict (1 dong)",
    "items": "order_id -> list[dict], GIU NGUYEN thu tu trong CSV",
    "payments": "order_id -> list[dict], GIU NGUYEN thu tu trong CSV",
    "customers": "customer_id -> dict",
    "products": "product_id -> dict",
    "sellers": "seller_id -> dict",
    "orders_by_unique_customer": "customer_unique_id -> list[order_id] theo thu tu CSV",
}

# Khong load geolocation (1000163 dong) va reviews: ca hai khong xuat hien trong output schema.
_CACHE: dict = {}


def _rows(filename: str, encoding: str = "utf-8"):
    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding=encoding) as fh:
        yield from csv.DictReader(fh)


def load_all() -> dict:
    """Dung 7 index mot lan roi cache lai. Goi nhieu lan chi ton chi phi lan dau."""
    if _CACHE:
        return _CACHE

    orders = {r["order_id"]: r for r in _rows("olist_orders_dataset.csv")}

    items = defaultdict(list)
    for r in _rows("olist_order_items_dataset.csv"):
        items[r["order_id"]].append(r)

    payments = defaultdict(list)
    for r in _rows("olist_order_payments_dataset.csv"):
        payments[r["order_id"]].append(r)

    customers = {r["customer_id"]: r for r in _rows("olist_customers_dataset.csv")}
    products = {r["product_id"]: r for r in _rows("olist_products_dataset.csv")}
    sellers = {r["seller_id"]: r for r in _rows("olist_sellers_dataset.csv")}

    # File translation co BOM o dau, nen tren cot dau la '﻿product_category_name'
    # neu mo bang utf-8 thuong. utf-8-sig cat BOM di.
    category_en = {
        r["product_category_name"]: r["product_category_name_english"]
        for r in _rows("product_category_name_translation.csv", encoding="utf-8-sig")
    }

    orders_by_unique = defaultdict(list)
    for order_id, order in orders.items():
        cust = customers.get(order["customer_id"])
        if cust:
            orders_by_unique[cust["customer_unique_id"]].append(order_id)

    _CACHE.update(
        orders=orders,
        items=dict(items),
        payments=dict(payments),
        customers=customers,
        products=products,
        sellers=sellers,
        orders_by_unique_customer=dict(orders_by_unique),
        category_en=category_en,
    )
    return _CACHE


def get_case_bundle(order_id: str) -> dict:
    """Tra ve: {order_id, order, items, payments, customer, products, sellers, customer_orders}.

    - order: dict hoac None neu order_id khong co trong CSV
    - items, payments: list, CO THE RONG (775 order khong co item row)
    - sellers: list seller_id duy nhat, theo thu tu xuat hien trong items
    - products: list dict san pham theo thu tu item, phan tu co the None
    - customer_orders: moi order_id cua cung customer_unique_id, ke ca order hien tai
    """
    idx = load_all()
    order = idx["orders"].get(order_id)
    items = idx["items"].get(order_id, [])
    payments = idx["payments"].get(order_id, [])
    if variants.PAYMENTS_SORTED_BY_SEQUENTIAL:
        # 9/50 case co payment nam khong tang dan trong CSV. Sap o day mot lan thi
        # payment_ids, payment_types va evidence_ids deu di theo, khong lech nhau.
        payments = sorted(payments, key=lambda p: int(p["payment_sequential"]))

    customer = idx["customers"].get(order["customer_id"]) if order else None

    seller_ids = []
    for it in items:
        if it["seller_id"] not in seller_ids:
            seller_ids.append(it["seller_id"])

    products = [idx["products"].get(it["product_id"]) for it in items]

    customer_orders = []
    if customer:
        customer_orders = idx["orders_by_unique_customer"].get(
            customer["customer_unique_id"], []
        )

    return {
        "order_id": order_id,
        "order": order,
        "items": items,
        "payments": payments,
        "customer": customer,
        "products": products,
        "sellers": seller_ids,
        "customer_orders": customer_orders,
    }


def _main(argv):
    if len(argv) < 2:
        print("dung: python -m src.datastore <order_id> | --stats")
        return 1

    if argv[1] == "--stats":
        idx = load_all()
        counts = defaultdict(int)
        for o in idx["orders"].values():
            counts[o["order_status"]] += 1
        for status, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"{status:<12} {n}")
        return 0

    bundle = get_case_bundle(argv[1])
    order = bundle["order"]
    if order is None:
        print(f"order_id        {argv[1]}")
        print("status          KHONG CO TRONG CSV")
        return 1

    print(f"order_id        {bundle['order_id']}")
    print(f"status          {order['order_status']}")
    print(f"items           {len(bundle['items'])}")
    print(f"sellers         {len(bundle['sellers'])}")
    print(f"payments        {len(bundle['payments'])}")
    print(f"delivered_at    {order['order_delivered_customer_date'] or 'null'}")
    print(f"estimated_at    {order['order_estimated_delivery_date'] or 'null'}")
    print(f"carrier_at      {order['order_delivered_carrier_date'] or 'null'}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
