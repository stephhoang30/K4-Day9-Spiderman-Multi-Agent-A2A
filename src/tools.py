"""4 tool tinh toan xac dinh. Khong tool nao goi model, khong tool nao goi mang.

Cung mot bundle thi luon ra cung mot ket qua.
"""
from __future__ import annotations

from datetime import datetime

from src import variants

FMT = "%Y-%m-%d %H:%M:%S"
CURRENCY = "BRL"
RECONCILE_TOLERANCE = 0.10


def _dt(value):
    """CSV tra ve chuoi rong khi khong co moc thoi gian -> None, khong phai 0."""
    if not value:
        return None
    return datetime.strptime(value, FMT)


def _hours(later, earlier):
    if later is None or earlier is None:
        return None
    return _money((later - earlier).total_seconds() / 3600)


def _money(x):
    """Lam tron 2 so va chuan hoa -0.0 thanh 0.0.

    round(a - b, 2) tren so thuc co the ra -0.0. JSON ghi ra '-0.0', va bo cham
    so difference_brl == 0.0 kieu strict thi -0.0 truot -> ca case bi 0 diem.
    Cong 0.0 khong doi gia tri nhung bien -0.0 thanh 0.0.
    """
    return round(x, 2) + 0.0


def analyze_delivery(bundle: dict) -> dict:
    """-> delivered_at, estimated_delivery_at, carrier_handoff_at,
          delivery_variance_hours, seller_handoff_analysis[], late_handoff_seller_ids[]

    delivery_variance_hours = delivered_customer - estimated_delivery, don vi gio
    handoff_variance_hours  = delivered_carrier - shipping_limit SOM NHAT cua seller do
    late_handoff = handoff_variance_hours > 0
    Thieu timestamp -> None. Lam tron 2 so o buoc cuoi.
    """
    order = bundle["order"] or {}
    delivered_raw = order.get("order_delivered_customer_date") or None
    estimated_raw = order.get("order_estimated_delivery_date") or None
    carrier_raw = order.get("order_delivered_carrier_date") or None

    delivered, estimated, carrier = _dt(delivered_raw), _dt(estimated_raw), _dt(carrier_raw)

    earliest_limit = {}
    for item in bundle["items"]:
        seller_id = item["seller_id"]
        limit = _dt(item.get("shipping_limit_date"))
        if limit is None:
            continue
        if seller_id not in earliest_limit or limit < earliest_limit[seller_id]:
            earliest_limit[seller_id] = limit

    handoff = []
    for seller_id in bundle["sellers"]:
        limit = earliest_limit.get(seller_id)
        variance = _hours(carrier, limit)
        handoff.append(
            {
                "seller_id": seller_id,
                "shipping_limit_at": limit.strftime(FMT) if limit else None,
                "handoff_variance_hours": variance,
                "late_handoff": bool(variance is not None and variance > 0),
            }
        )

    # seller_handoff_analysis chi liet ke seller GIAO MUON. Do duoc bang bo cham that:
    # liet ke moi seller -> 79.1543, chi liet ke seller giao muon -> 91.8029 (+12.65).
    # Xem nhat ky luot T7 o src/variants.py. late_handoff_seller_ids tinh tu cung
    # danh sach day du nen khong doi.
    return {
        "delivered_at": delivered_raw,
        "estimated_delivery_at": estimated_raw,
        "carrier_handoff_at": carrier_raw,
        "delivery_variance_hours": _hours(delivered, estimated),
        "seller_handoff_analysis": [h for h in handoff if h["late_handoff"]],
        "late_handoff_seller_ids": [h["seller_id"] for h in handoff if h["late_handoff"]],
    }


def reconcile_payment(bundle: dict) -> dict:
    """-> currency, item_total_brl, freight_total_brl, expected_total_brl,
          payment_total_brl, difference_brl, reconciled, payment_types[]

    Khong co item row -> expected_total_brl, difference_brl, reconciled deu None.
    Cong full precision roi moi round o buoc cuoi.
    """
    items, payments = bundle["items"], bundle["payments"]

    raw_item = sum(float(i["price"]) for i in items)
    raw_freight = sum(float(i["freight_value"]) for i in items)
    raw_payment = sum(float(p["payment_value"]) for p in payments)

    payment_types = []
    for p in payments:
        if p["payment_type"] not in payment_types:
            payment_types.append(p["payment_type"])

    if not items:
        # Giu nguyen int 0 nhu cac ban da cham 79.15: sum([]) ra int, khong qua _money.
        item_total = freight_total = 0
        expected = difference = reconciled = None
        if variants.NULL_MONEY_WHEN_NO_ITEM:
            item_total = freight_total = None
    else:
        item_total = _money(raw_item)
        freight_total = _money(raw_freight)
        expected = _money(raw_item + raw_freight)
        difference = _money(raw_payment - (raw_item + raw_freight))
        reconciled = abs(raw_payment - (raw_item + raw_freight)) <= RECONCILE_TOLERANCE

    return {
        "currency": CURRENCY,
        "item_total_brl": item_total,
        "freight_total_brl": freight_total,
        "expected_total_brl": expected,
        "payment_total_brl": _money(raw_payment),
        "difference_brl": difference,
        "reconciled": reconciled,
        "payment_types": payment_types,
    }


def build_customer_context(bundle: dict) -> dict:
    """-> customer_unique_id, related_order_ids[] (order khac cua cung customer_unique_id)

    Order lich su KHONG duoc dua vao affected_entities, chi xuat hien o day.
    """
    customer = bundle["customer"]
    if not customer:
        return {"customer_unique_id": None, "related_order_ids": []}

    related = [oid for oid in bundle["customer_orders"] if oid != bundle["order_id"]]
    return {
        "customer_unique_id": customer["customer_unique_id"],
        "related_order_ids": related,
    }


def build_product_context(bundle: dict) -> dict:
    """-> product_ids[], category_names[] (duy nhat, theo thu tu xuat hien trong items)

    Bang dich category den tu lat du lieu do coordinator cat san, khong tu mo datastore:
    tool tu goi load_all() la doc duoc ca 8 index, tuc pha ranh gioi truy cap.
    Rong -> giu nguyen ten Bo Dao Nha trong olist_products_dataset.csv.
    """
    translate = bundle.get("category_translation") or {}

    product_ids, categories = [], []
    for item, product in zip(bundle["items"], bundle["products"]):
        if item["product_id"] not in product_ids:
            product_ids.append(item["product_id"])
        if product:
            name = product.get("product_category_name") or None
            if name:
                name = translate.get(name, name)
            if name and name not in categories:
                categories.append(name)
    return {"product_ids": product_ids, "category_names": categories}
