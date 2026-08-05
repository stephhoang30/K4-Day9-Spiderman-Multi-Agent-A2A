"""Builder cho evidence ID theo đúng 5 định dạng ở README mục 5.

Chỉ evidence dựng được trực tiếp từ dữ liệu đã tải mới được đưa vào; evidence
không tồn tại trong CSV bị tính false positive nên caller phải truyền vào các
ID đã được xác nhận tồn tại (item_ids/payment_ids lấy từ affected_entities đã
capped, seller_ids chỉ gồm seller chịu trách nhiệm).
"""

MAX_EVIDENCE = 20


def build_evidence_ids(
    order_id: str,
    item_ids: list[str],
    payment_ids: list[str],
    responsible_seller_ids: list[str],
    cause_codes: list[str],
) -> list[str]:
    evidence = [f"order:{order_id}"]
    evidence += [f"item:{iid}" for iid in item_ids]
    evidence += [f"payment:{pid}" for pid in payment_ids]
    evidence += [f"seller:{sid}" for sid in responsible_seller_ids]
    evidence += [f"policy:{code}" for code in cause_codes]
    return evidence[:MAX_EVIDENCE]
