"""Moi primary issue mot case that, lay tu 99441 order trong CSV.

Chay: python tests/test_policy.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test chot hanh vi theo dung van ban de, khong theo bien the dang thu nghiem.
os.environ["BASELINE"] = "1"

from src.datastore import get_case_bundle
from src.policy import classify
from src.tools import (
    analyze_delivery,
    build_customer_context,
    build_product_context,
    reconcile_payment,
)

DEMO = "0e3ec3c17b64c6cc7bc01bba21e7afdf"


def _classify(order_id):
    bundle = get_case_bundle(order_id)
    analysis = {
        "delivery": analyze_delivery(bundle),
        "payment": reconcile_payment(bundle),
        "customer": build_customer_context(bundle),
        "product": build_product_context(bundle),
    }
    return bundle, classify(bundle, analysis)


def test_1_canceled_order_paid():
    _, r = _classify("1b9ecfe83cdc259250e1a8aca174f0ad")
    assert r["case_assessment"]["primary_issue"] == "canceled_order_paid"
    assert r["financial_resolution"]["recommended_refund_brl"] == 33.34
    assert r["resolution_actions"][0] == "issue_full_refund"
    assert r["root_cause_analysis"]["responsible_parties"][0]["party_id"] == "OLIST_PLATFORM"


def test_2_unavailable_order_paid():
    _, r = _classify("dc18a044b56ed174037ca164cdf2e921")
    assert r["case_assessment"]["primary_issue"] == "unavailable_order_paid"
    assert r["case_assessment"]["case_status"] == "action_required"
    assert "verify_refund_completion" in r["resolution_actions"]


def test_3_late_delivery_seller():
    _, r = _classify(DEMO)
    a = r["case_assessment"]
    assert a["primary_issue"] == "late_delivery_seller"
    assert a["secondary_issues"] == ["multi_item_order", "split_payment"]
    assert r["financial_resolution"]["recommended_refund_brl"] == 25.52
    assert r["root_cause_analysis"]["ranked_causes"] == [
        {"cause_code": "SELLER_HANDOFF_AFTER_LIMIT", "rank": 1}
    ]
    assert r["root_cause_analysis"]["responsible_parties"] == [
        {"party_type": "seller", "party_id": "cca3071e3e9bb7d12640c9fbe2301306"}
    ]
    assert r["resolution_actions"] == [
        "refund_freight",
        "review_seller_handoff",
        "verify_payment_allocation",
    ]


def test_4_late_delivery_logistics():
    _, r = _classify("fbf9ac61453ac646ce8ad9783d7d0af6")
    assert r["case_assessment"]["primary_issue"] == "late_delivery_logistics"
    assert r["root_cause_analysis"]["responsible_parties"][0]["party_id"] == "LOGISTICS_PROVIDER"
    assert "review_carrier_delay" in r["resolution_actions"]


def test_5_valid_split_payment():
    _, r = _classify("e481f51cbdc54678b7cc49136f2d6af7")
    assert r["case_assessment"]["primary_issue"] == "valid_split_payment"
    assert r["case_assessment"]["case_status"] == "no_action"
    assert r["financial_resolution"]["recommended_refund_brl"] == 0.0
    # Action chinh da giai thich split payment roi.
    assert "verify_payment_allocation" not in r["resolution_actions"]


def test_6_unsupported_late_claim():
    _, r = _classify("53cdb2fc8bc7dce0b6741e2150273451")
    assert r["case_assessment"]["primary_issue"] == "unsupported_late_claim"
    assert r["resolution_actions"] == ["reject_late_refund"]
    assert r["financial_resolution"]["recommended_refund_brl"] == 0.0


def test_7_uu_tien_canceled_hon_late():
    """Order vua canceled vua giao tre chi duoc nhan mot primary issue."""
    bundle = get_case_bundle("1b9ecfe83cdc259250e1a8aca174f0ad")
    analysis = {
        "delivery": {
            "delivered_at": "2018-01-10 00:00:00",
            "estimated_delivery_at": "2018-01-01 00:00:00",
            "carrier_handoff_at": "2017-12-20 00:00:00",
            "delivery_variance_hours": 216.0,
            "seller_handoff_analysis": [],
            "late_handoff_seller_ids": ["seller_gia_dinh"],
        },
        "payment": reconcile_payment(bundle),
        "customer": build_customer_context(bundle),
        "product": build_product_context(bundle),
    }
    r = classify(bundle, analysis)
    assert r["case_assessment"]["primary_issue"] == "canceled_order_paid"


def test_8_evidence_id_dung_dang():
    bundle, r = _classify(DEMO)
    order_id = bundle["order_id"]
    assert r["evidence_ids"][0] == f"order:{order_id}"
    assert f"item:{order_id}:1" in r["evidence_ids"]
    assert f"payment:{order_id}:2" in r["evidence_ids"]
    assert "policy:SELLER_HANDOFF_AFTER_LIMIT" in r["evidence_ids"]
    assert len(r["evidence_ids"]) <= 20


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
