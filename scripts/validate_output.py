"""Self-check script chạy TRƯỚC KHI nộp bài — không có ground-truth để so sánh.

Chỉ kiểm tra tính HỢP LỆ NỘI TẠI của output/EC_0xx.json so với input/EC_0xx.json:
  - Đủ 50 file output (hard-gate nếu thiếu).
  - JSON parse được và pass pydantic `core.schemas.CaseOutput` (hard-gate nếu không).
  - Mọi evidence_id đúng 1 trong 5 pattern của README mục 5 VÀ ID tham chiếu
    (order/item/payment/seller) THẬT SỰ tồn tại trong CSV gốc qua `get_store()`
    (hard-gate — đây là "false positive" README mục 5 cảnh báo).
  - Các bất biến nghiệp vụ khác (rounding 2 chữ số, case_status <-> refund,
    valid_split_payment không kèm verify_payment_allocation, null-handling khi
    order không có item) — báo lỗi rõ ràng nhưng KHÔNG tự ý gán là hard-gate vì
    README chỉ liệt kê 4 loại hard-gate ở trên (thiếu điểm theo trọng số ở mục 8,
    không bị chấm 0 điểm case).

Chạy: `uv run python scripts/validate_output.py` từ root repo.
Exit code: 1 nếu có bất kỳ case nào fail hard-gate, 0 nếu ngược lại.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Cho phep chay truc tiep `uv run python scripts/validate_output.py` tu root repo:
# script nam trong scripts/, nen can them thu muc goc vao sys.path truoc khi
# import cac module `core.*` (khong dua vao viec goi qua `python -m`).
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pydantic import ValidationError  # noqa: E402

from core.data_loader import get_store  # noqa: E402
from core.schemas import CaseOutput  # noqa: E402
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
NUM_CASES = 50

# README mục 5 — 5 pattern evidence hợp lệ, anchor chặt để không lọt định dạng sai.
# order_id/seller_id Olist là hex 32 ký tự (verify bằng orders['order_id'].iloc[0]).
EVIDENCE_PATTERNS: dict[str, re.Pattern[str]] = {
    "order": re.compile(r"^order:[0-9a-f]{32}$"),
    "item": re.compile(r"^item:([0-9a-f]{32}):(\d+)$"),
    "payment": re.compile(r"^payment:([0-9a-f]{32}):(\d+)$"),
    "seller": re.compile(r"^seller:[0-9a-f]{32}$"),
    "policy": re.compile(
        r"^policy:(SELLER_HANDOFF_AFTER_LIMIT|CARRIER_DELIVERED_AFTER_ESTIMATE|"
        r"ORDER_CANCELED_AFTER_PAYMENT|ORDER_UNAVAILABLE_AFTER_PAYMENT|"
        r"MULTIPLE_PAYMENTS_RECONCILED|DELIVERY_WITHIN_ESTIMATE)$"
    ),
}

# Field tiền tệ / giờ phải làm tròn đúng 2 chữ số thập phân (README mục 4).
ROUNDED_PAYMENT_FIELDS = [
    "item_total_brl",
    "freight_total_brl",
    "expected_total_brl",
    "payment_total_brl",
    "difference_brl",
]
ROUND_TOLERANCE = 1e-9


@dataclass
class CaseResult:
    case_id: str
    hard_gate_errors: list[str] = field(default_factory=list)
    invariant_errors: list[str] = field(default_factory=list)

    @property
    def all_errors(self) -> list[str]:
        return self.hard_gate_errors + self.invariant_errors

    @property
    def passed(self) -> bool:
        return not self.all_errors

    @property
    def has_hard_gate(self) -> bool:
        return bool(self.hard_gate_errors)


def is_rounded_to_2dp(value: float) -> bool:
    return abs(round(value, 2) - value) < ROUND_TOLERANCE


def check_evidence_ids(evidence_ids: list[str], store) -> tuple[list[str], list[str]]:
    """Trả về (hard_gate_errors, invariant_errors) cho danh sách evidence_ids."""
    hard_errors: list[str] = []

    for eid in evidence_ids:
        matched_kind: str | None = None
        match: re.Match[str] | None = None
        for kind, pattern in EVIDENCE_PATTERNS.items():
            m = pattern.match(eid)
            if m is not None:
                matched_kind = kind
                match = m
                break

        if matched_kind is None:
            hard_errors.append(
                f"evidence_id '{eid}' khong khop bat ky pattern hop le nao "
                f"(order:/item:/payment:/seller:/policy: - xem README muc 5)"
            )
            continue

        assert match is not None
        if matched_kind == "order":
            order_id = eid.split(":", 1)[1]
            if store.get_order(order_id) is None:
                hard_errors.append(
                    f"evidence_id '{eid}' tham chieu order_id khong ton tai trong orders.csv"
                )
        elif matched_kind == "item":
            order_id, item_id_str = match.group(1), match.group(2)
            items = store.get_items(order_id)
            item_ids = {int(it["order_item_id"]) for it in items}
            if int(item_id_str) not in item_ids:
                hard_errors.append(
                    f"evidence_id '{eid}' tham chieu item khong ton tai trong "
                    f"order_items.csv (order_id={order_id}, order_item_id={item_id_str})"
                )
        elif matched_kind == "payment":
            order_id, seq_str = match.group(1), match.group(2)
            payments = store.get_payments(order_id)
            seqs = {int(p["payment_sequential"]) for p in payments}
            if int(seq_str) not in seqs:
                hard_errors.append(
                    f"evidence_id '{eid}' tham chieu payment khong ton tai trong "
                    f"order_payments.csv (order_id={order_id}, payment_sequential={seq_str})"
                )
        elif matched_kind == "seller":
            seller_id = eid.split(":", 1)[1]
            if store.get_seller(seller_id) is None:
                hard_errors.append(
                    f"evidence_id '{eid}' tham chieu seller_id khong ton tai trong sellers.csv"
                )
        # "policy" kind: chi can dung format, khong co CSV nao de doi chieu.

    return hard_errors, []


def check_business_invariants(parsed: CaseOutput) -> list[str]:
    """Cac bat bien nghiep vu khong the hien duoc bang pydantic Field mot minh."""
    errors: list[str] = []

    # confidence trong [0,1] - pydantic da enforce, double-check khong hai.
    confidence = parsed.case_assessment.confidence
    if not (0.0 <= confidence <= 1.0):
        errors.append(f"confidence={confidence} nam ngoai [0, 1]")

    # Rounding 2 chu so thap phan cho field tien / gio.
    pr = parsed.payment_reconciliation
    for f in ROUNDED_PAYMENT_FIELDS:
        value = getattr(pr, f)
        if value is not None and not is_rounded_to_2dp(value):
            errors.append(f"payment_reconciliation.{f}={value} khong lam tron 2 chu so thap phan")

    refund = parsed.financial_resolution.recommended_refund_brl
    if refund is not None and not is_rounded_to_2dp(refund):
        errors.append(f"financial_resolution.recommended_refund_brl={refund} khong lam tron 2 chu so thap phan")

    da = parsed.delivery_analysis
    if da.delivery_variance_hours is not None and not is_rounded_to_2dp(da.delivery_variance_hours):
        errors.append(
            f"delivery_analysis.delivery_variance_hours={da.delivery_variance_hours} "
            f"khong lam tron 2 chu so thap phan"
        )
    for idx, sha in enumerate(da.seller_handoff_analysis):
        if sha.handoff_variance_hours is not None and not is_rounded_to_2dp(sha.handoff_variance_hours):
            errors.append(
                f"delivery_analysis.seller_handoff_analysis[{idx}].handoff_variance_hours="
                f"{sha.handoff_variance_hours} khong lam tron 2 chu so thap phan"
            )

    # case_status <-> recommended_refund_brl phai nhat quan.
    status = parsed.case_assessment.case_status
    if status == "action_required" and not (refund > 0):
        errors.append(
            f"case_status='action_required' nhung recommended_refund_brl={refund} khong > 0"
        )
    if status == "no_action" and abs(refund) >= ROUND_TOLERANCE:
        errors.append(
            f"case_status='no_action' nhung recommended_refund_brl={refund} khac 0"
        )

    # valid_split_payment khong duoc kem verify_payment_allocation (README muc 4 dong cuoi).
    if parsed.case_assessment.primary_issue == "valid_split_payment":
        if "verify_payment_allocation" in parsed.resolution_actions:
            errors.append(
                "primary_issue='valid_split_payment' nhung resolution_actions "
                "chua 'verify_payment_allocation' (khong duoc phep theo README muc 4)"
            )

    # Order khong co item -> expected_total_brl/difference_brl/reconciled phai la null.
    if not parsed.affected_entities.item_ids:
        if pr.expected_total_brl is not None:
            errors.append(
                "affected_entities.item_ids rong nhung payment_reconciliation.expected_total_brl "
                "khong phai null"
            )
        if pr.difference_brl is not None:
            errors.append(
                "affected_entities.item_ids rong nhung payment_reconciliation.difference_brl "
                "khong phai null"
            )
        if pr.reconciled is not None:
            errors.append(
                "affected_entities.item_ids rong nhung payment_reconciliation.reconciled "
                "khong phai null"
            )

    return errors


def validate_case(idx: int, store) -> CaseResult:
    case_id = f"EC_{idx:03d}"
    result = CaseResult(case_id=case_id)

    output_path = OUTPUT_DIR / f"{case_id}.json"
    if not output_path.exists():
        result.hard_gate_errors.append(f"Thieu file output: {output_path}")
        return result

    try:
        raw_text = output_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        result.hard_gate_errors.append(f"JSON khong parse duoc: {e}")
        return result
    except OSError as e:
        result.hard_gate_errors.append(f"Khong doc duoc file: {e}")
        return result

    try:
        parsed = CaseOutput(**data)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(part) for part in err["loc"])
            result.hard_gate_errors.append(f"ValidationError field '{loc}': {err['msg']}")
        return result

    if parsed.case_id != case_id:
        result.invariant_errors.append(
            f"case_id trong file ('{parsed.case_id}') khac ten file mong doi ('{case_id}')"
        )

    evidence_hard_errors, evidence_invariant_errors = check_evidence_ids(parsed.evidence_ids, store)
    result.hard_gate_errors.extend(evidence_hard_errors)
    result.invariant_errors.extend(evidence_invariant_errors)

    result.invariant_errors.extend(check_business_invariants(parsed))

    return result


def main() -> int:
    if not INPUT_DIR.is_dir():
        print(f"Khong tim thay thu muc input: {INPUT_DIR}", file=sys.stderr)
        return 1

    store = get_store()

    results: list[CaseResult] = [validate_case(idx, store) for idx in range(1, NUM_CASES + 1)]

    total = len(results)
    num_passed = sum(1 for r in results if r.passed)
    num_hard_gate = sum(1 for r in results if r.has_hard_gate)
    num_invariant_only = sum(
        1 for r in results if not r.has_hard_gate and r.invariant_errors
    )

    print("=" * 72)
    print("VALIDATE OUTPUT REPORT")
    print("=" * 72)
    for r in results:
        if r.passed:
            print(f"[PASS] {r.case_id}")
            continue
        tag = "HARD-GATE FAIL" if r.has_hard_gate else "FAIL (invariant)"
        print(f"[{tag}] {r.case_id}")
        for err in r.hard_gate_errors:
            print(f"    - [hard-gate] {err}")
        for err in r.invariant_errors:
            print(f"    - [invariant] {err}")

    print("-" * 72)
    print(f"Tong so case: {total}")
    print(f"  PASS (khong loi nao):            {num_passed}")
    print(f"  FAIL - hard-gate (0 diem case):  {num_hard_gate}")
    print(f"  FAIL - chi vi pham bat bien:     {num_invariant_only}")
    print("=" * 72)

    if num_hard_gate > 0:
        print(f"KET QUA: FAIL - co {num_hard_gate} case fail hard-gate. Khong nen nop bai.")
        return 1

    print("KET QUA: PASS - khong co case nao fail hard-gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
