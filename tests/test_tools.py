"""8 assert cho src/tools.py, doi chieu truc tiep voi CSV.

Chay bang python tran: python tests/test_tools.py
Chay duoc ca bang pytest neu may co pytest.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test chot hanh vi theo dung van ban de, khong theo bien the dang thu nghiem.
os.environ["BASELINE"] = "1"

from src.datastore import get_case_bundle
from src.tools import (
    analyze_delivery,
    build_customer_context,
    build_product_context,
    reconcile_payment,
)

DEMO = "0e3ec3c17b64c6cc7bc01bba21e7afdf"
NO_ITEM = "8e24261a7e58791d10cb1bf9da94df5c"  # status unavailable, khong co item row


def test_delivery_variance():
    d = analyze_delivery(get_case_bundle(DEMO))
    assert d["delivery_variance_hours"] == 317.79, d["delivery_variance_hours"]


def test_handoff_variance():
    d = analyze_delivery(get_case_bundle(DEMO))
    assert d["seller_handoff_analysis"][0]["handoff_variance_hours"] == 17.56


def test_late_handoff_seller_ids():
    d = analyze_delivery(get_case_bundle(DEMO))
    assert len(d["late_handoff_seller_ids"]) == 1, d["late_handoff_seller_ids"]


def test_item_total():
    p = reconcile_payment(get_case_bundle(DEMO))
    assert p["item_total_brl"] == 119.80, p["item_total_brl"]


def test_freight_total():
    p = reconcile_payment(get_case_bundle(DEMO))
    assert p["freight_total_brl"] == 25.52, p["freight_total_brl"]


def test_payment_total():
    p = reconcile_payment(get_case_bundle(DEMO))
    assert p["payment_total_brl"] == 145.32, p["payment_total_brl"]


def test_difference():
    p = reconcile_payment(get_case_bundle(DEMO))
    assert p["difference_brl"] == 0.00, p["difference_brl"]


def test_reconciled():
    p = reconcile_payment(get_case_bundle(DEMO))
    assert p["reconciled"] is True, p["reconciled"]


def test_no_item_order_tra_null():
    p = reconcile_payment(get_case_bundle(NO_ITEM))
    assert p["expected_total_brl"] is None
    assert p["difference_brl"] is None
    assert p["reconciled"] is None


def test_payment_giu_thu_tu_csv():
    b = get_case_bundle(DEMO)
    assert [p["payment_sequential"] for p in b["payments"]] == ["2", "1"]


def test_customer_va_product_context():
    b = get_case_bundle(DEMO)
    c = build_customer_context(b)
    assert c["customer_unique_id"] == "fc3ae503d8cbc4c02a2d8e467b7bbfe5"
    assert c["related_order_ids"] == []
    assert build_product_context(b)["category_names"] == ["moveis_decoracao"]


def _run():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    passed, failed = 0, []
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except AssertionError as exc:
            failed.append(f"{name}: {exc}")
    for line in failed:
        print("FAIL", line)
    print(f"OK {passed}/{len(tests)}")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(_run())
