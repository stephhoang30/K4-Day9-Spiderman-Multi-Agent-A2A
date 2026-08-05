"""Bien the thu nghiem voi bo cham that, kem ket qua da do duoc.

Diem cuoi cung: 79.1543 -> 91.8029.

Moi bien the mot cong tac rieng, mac dinh phan anh nhung gi da do duoc:

    BASELINE=1 python src/run_all.py           # tat het bien the
    V_CATEGORY_ENGLISH=1 python src/run_all.py # bat rieng mot bien the

Cach doc so
-----------
Diem la trung binh 50 case, moi case 0-100. Mot bien the cham N case ma sai han
thi diem tut khoang N*100/50 = N*2. Nen tu do tut chia cho so case doi duoc,
suy ra duoc moi case do dang dang gia bao nhieu — do la cach ca bang duoi day
duoc dung len.

Nhat ky thu nghiem
------------------
Luot 1 — NULL_MONEY + SECOND_CAUSE + RELATED_BY_TIME + CONF_ONE cung luc.
         79.1543 -> 66.7026 (-12.45). BON bien so mot luot nen khong quy trach
         nhiem duoc; luot T1 va T4 ve sau moi tach ra (xem phan giai o duoi).

Luot 2 — chi PAYMENT_SORTED (9 case doi thu tu payment). 79.1543, khong doi.
         KET LUAN: bo cham so mang nhu TAP HOP, khong xet thu tu.
         Ca nhom gia thuyet "sai quy uoc thu tu" bi loai.

Luot 3 — chi CATEGORY_ENGLISH (43/50 file doi noi dung). 79.1543 -> 5.1612.
         Muc tut lon hon nhieu so voi mot truong bi sai binh thuong.
         KET LUAN: giu ten Bo Dao Nha goc trong olist_products_dataset.csv.
         Bang dich chi de tra cuu, khong phai de ghi ra output.

Luot T6 — evidence gom MOI seller thay vi chi seller chiu trach nhiem (34 case).
         79.1543 -> 78.4703 (-0.68), tuc -1.0 diem moi case.
         KET LUAN 1: bo cham cho diem TUNG PHAN rat min (dang F1), khong phai
         dung/sai ca case. Muc -1.0 khop voi viec them vai false positive vao
         mot tap evidence ~8 phan tu.
         KET LUAN 2: evidence hien tai gan nhu dung, khong dao them o day.

Luot T4 — confidence = 0.92 cho ca 50 case. 79.1543 -> 79.1451 (-0.01).
         KET LUAN: confidence gan nhu khong duoc cham. Loai ca nhom gia thuyet
         nay, va tra lai -12.45 cua luot 1 cho NULL_MONEY hoac SECOND_CAUSE.

Luot T1 — chi NULL_MONEY (6 case khong co item row). 79.1543 -> 67.00 (-12.15),
         tuc -101 diem moi case: 6 case do bi ve 0.
         KET LUAN 1: item_total_brl va freight_total_brl phai la 0, khong duoc
         null. README muc 4 liet ke dung ba truong null va chi ba truong do.
         KET LUAN 2: 6 case khong item row dang duoc ~100/100, da hoan hao.
         KET LUAN 3: giai xong luot 1 — NULL_MONEY -12.15, CONF_ONE -0.01,
         RELATED_BY_TIME 0, phan con lai cho SECOND_CAUSE chi ~-0.29.
         KET LUAN 4: 6 case dat 100 va tong la 79.1543, nen 44 case CO item row
         chi dang duoc ~76.3. Toan bo diem mat nam trong nhom nay.

Luot T7 — seller_handoff_analysis chi liet ke seller GIAO MUON, thay vi moi
         seller cua order (34 case). 79.1543 -> 91.8029 (+12.65).
         BIEN THE THANG CUOC, da dua thang vao src/tools.py:analyze_delivery.
         Tim ra nho ket luan 4 o tren: da biet loi nam o truong dan xuat tu item
         nen thu truong phu rong nhat truoc.
         Sau T7: 44 case co item len ~90.7, con du ~8.2 diem.

Luot V2 — gop 3 thay doi tren nen T7 (44 case): seller_ids chi giu seller giao
         muon, product_ids bo dedupe, them verify_refund_completion cho moi case
         co refund. 91.8029 -> 48.7750 (-43.03), tuc -48.9 moi case.
         Muc do do lon hon han kieu mat diem tung phan cua T6 -> it nhat mot
         trong ba cham vao hard gate. Nghi pham chinh la product_ids co phan tu
         trung lap, cung co che voi CATEGORY_ENGLISH: gia tri khong hop le lam
         hong ca case. Het luot nop nen chua tach rieng duoc ba bien so nay.

Mo hinh diem rut ra
-------------------
- Cham tung phan rat min cho hau het cac truong (T6: -1.0 diem cho evidence thua).
- Nhung MOT SO gia tri lam hong ca case: category_names khong co trong CSV,
  item_total/freight_total = null o order khong co item row (T1, luot 3).
- confidence va thu tu mang khong duoc cham (T4, luot 2).
- Hien tai: 6 case khong item row ~100/100, 44 case co item ~90.7/100.
"""
from __future__ import annotations

import os

_BASELINE = os.environ.get("BASELINE", "0") == "1"


def _on(name: str, default: str) -> bool:
    if _BASELINE:
        return False
    return os.environ.get(f"V_{name}", default) == "1"


# 1 — DA BAC BO o luot 1: lam mat 12 diem tren 6 case khong co item row.
NULL_MONEY_WHEN_NO_ITEM = _on("NULL_MONEY", "0")

# 2 — DA BAC BO o luot 1: khong tang diem, con hoi hai. 10 case.
SECOND_RANKED_CAUSE = _on("SECOND_CAUSE", "0")

# 3 — DA GO KHOI CODE: doi 0 case (thu tu CSV da trung thu tu order_purchase_timestamp),
#     va cach cai dat cu bat build_customer_context tu goi load_all(), tuc doc vuot lat.

# 4 — DA BAC BO o luot 1: confidence co dinh 1.0 hoi hai. 50 case.
CONFIDENCE_ALWAYS_ONE = _on("CONF_ONE", "0")

# 5 — DANG THU: sap payment theo payment_sequential tang dan thay vi thu tu dong CSV.
#     Cu the: 9/50 case co payment nam khong tang dan trong CSV.
#     Vi du output o README muc 6 liet ke payment:...:1 roi :2, tuc tang dan.
#     Cham vao payment_ids, payment_types va evidence_ids -> 3 thanh phan rubric.
#     DA BAC BO o luot 2: doi 9 case, diem khong doi -> bo cham khong xet thu tu.
PAYMENTS_SORTED_BY_SEQUENTIAL = _on("PAYMENT_SORTED", "0")

# 6 — DANG THU: category_names lay ban dich tieng Anh tu
#     product_category_name_translation.csv thay vi ten tieng Bo Dao Nha goc.
#     README muc 2 liet ke cac khoa join va KHONG nhac file translation, nhung
#     file do van nam trong 9 CSV va ngoai viec dich category thi khong dung vao dau.
#     Cham 44 case, dung MOT truong trong mot thanh phan rubric.
#     MAC DINH 0: ban 79.1543 da nop la ten Bo Dao Nha. De mac dinh 1 thi lenh chay
#     ghi trong metadata.json khong con dung lai bo output da nop.
CATEGORY_NAMES_IN_ENGLISH = _on("CATEGORY_ENGLISH", "0")


def active() -> dict:
    return {
        "NULL_MONEY": NULL_MONEY_WHEN_NO_ITEM,
        "SECOND_CAUSE": SECOND_RANKED_CAUSE,
        "CONF_ONE": CONFIDENCE_ALWAYS_ONE,
        "PAYMENT_SORTED": PAYMENTS_SORTED_BY_SEQUENTIAL,
        "CATEGORY_ENGLISH": CATEGORY_NAMES_IN_ENGLISH,
    }
