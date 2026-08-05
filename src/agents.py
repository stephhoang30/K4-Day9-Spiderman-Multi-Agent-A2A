"""7 agent. Moi agent chi nhan dung phan du lieu cua minh, khong nhan ca bundle.

Ranh gioi quyen truy cap la co che that: coordinator cat lat du lieu truoc khi gui,
nen mot agent khong the doc bang khong thuoc ve no du co muon.

Chi 2 trong 7 agent goi model (coordinator, verifier). 4 agent du lieu goi tool
xac dinh o src/tools.py; policy agent goi luat o src/policy.py.
"""
from __future__ import annotations

from src import bus, llm, tools, variants, verifier

MAX_ORDER_IDS = 5
MAX_ITEM_IDS = 5
MAX_SELLER_IDS = 3
MAX_PAYMENT_IDS = 5
MAX_RELATED_ORDERS = 5
MAX_PRODUCT_IDS = 5
MAX_CATEGORIES = 5
MAX_ACTIONS = 5

DATA_AGENTS = ["customer", "order_product", "payment", "delivery"]
ALL_AGENTS = DATA_AGENTS + ["policy", "verifier"]


def _cap(values, limit):
    return list(values)[:limit]


def _category_translation() -> dict:
    """Coordinator la ben duy nhat duoc mo datastore, nen no lay bang dich o day.

    Rong khi bien the CATEGORY_ENGLISH tat -> category_names giu ten Bo Dao Nha goc.
    """
    if not variants.CATEGORY_NAMES_IN_ENGLISH:
        return {}
    from src.datastore import load_all

    return load_all()["category_en"]


# --- 4 agent du lieu: khong agent nao goi model ---------------------------------


def customer_agent(payload: dict) -> dict:
    """Doc: customers, orders. Tra: customer_context."""
    return tools.build_customer_context(payload["slice"])


def order_product_agent(payload: dict) -> dict:
    """Doc: items, products, sellers. Tra: affected_entities (phan order/item/seller) + product_context."""
    data = payload["slice"]
    order_id = data["order_id"]
    return {
        "order_ids": [order_id],
        "item_ids": [f"{order_id}:{i['order_item_id']}" for i in data["items"]],
        "seller_ids": list(data["sellers"]),
        "product_context": tools.build_product_context(data),
    }


def payment_agent(payload: dict) -> dict:
    """Doc: payments, items. Tra: payment_reconciliation + payment_ids."""
    data = payload["slice"]
    order_id = data["order_id"]
    return {
        "payment_reconciliation": tools.reconcile_payment(data),
        "payment_ids": [f"{order_id}:{p['payment_sequential']}" for p in data["payments"]],
    }


def delivery_agent(payload: dict) -> dict:
    """Doc: orders, items. Tra: delivery_analysis."""
    return tools.analyze_delivery(payload["slice"])


# --- Policy agent: luat, khong model -------------------------------------------


def policy_agent(payload: dict) -> dict:
    """Doc: ket qua 4 agent tren. Tra: case_assessment, root_cause_analysis,
    financial_resolution, resolution_actions, evidence_ids."""
    from src.policy import classify

    return classify(payload["bundle"], payload["analysis"])


# --- Verifier agent: co goi model ----------------------------------------------

VERIFIER_SYSTEM = (
    "Ban la Verifier cua he thong xu ly khieu nai. Ban nhan mot ban tom tat ket luan "
    "kem truong deterministic_errors — danh sach loi ma bo kiem xac dinh tim ra. "
    "Quy tac: deterministic_errors rong ([]) nghia la KHONG con loi nao, khi do approved = true. "
    "Chi tra approved = false khi danh sach do co it nhat mot loi. "
    'Tra ve DUNG mot JSON object dang {"approved": true/false, "note": "mot cau ngan"}. '
    "Khong giai thich them."
)


def verifier_agent(payload: dict) -> dict:
    """Doc: JSON da dung xong. Tra: danh sach loi (rong nghia la dat).

    Bo kiem xac dinh o src/verifier.py la quyet dinh cuoi cung. Model chi them
    mot nhan xet vao trace; no khong duoc phep lat ket luan cua bo kiem.
    """
    result = payload["result"]
    errors = verifier.verify(result)

    summary = {
        "case_id": result.get("case_id"),
        "primary_issue": result["case_assessment"]["primary_issue"],
        "case_status": result["case_assessment"]["case_status"],
        "refund_brl": result["financial_resolution"]["recommended_refund_brl"],
        "deterministic_errors": errors,
    }
    reply = llm.extract_json(
        llm.chat(VERIFIER_SYSTEM, "Ban tom tat:\n" + repr(summary))
    )
    return {
        "errors": errors,
        "llm_review": reply if isinstance(reply, dict) else None,
    }


# --- Coordinator: co goi model --------------------------------------------------

ROUTER_SYSTEM = (
    "Ban la Coordinator dieu phoi 6 agent trong he thong xu ly khieu nai thuong mai dien tu:\n"
    "- customer_agent: doc bang customers, tra ve lich su order cua khach\n"
    "- order_product_agent: doc item, product, seller cua order\n"
    "- payment_agent: doi soat payment voi item cong freight\n"
    "- delivery_agent: tinh chenh lech giao hang va ban giao cho carrier\n"
    "- policy_agent: ap dung EC_POLICY_V2. CAN ket qua cua ca 4 agent tren.\n"
    "- verifier_agent: kiem schema output. CAN ket qua cua policy_agent.\n\n"
    "Ban nhan danh sach agent DA CHAY va danh sach CHUA CHAY. "
    "Chon DUNG MOT agent trong danh sach chua chay de chay tiep, "
    "ton trong rang buoc phu thuoc o tren.\n"
    'Tra ve DUNG mot JSON object: {"next": "<ten_agent>"}. Khong giai thich.'
)

# Rang buoc phu thuoc that: policy can du 4 lat du lieu, verifier can ket luan cua policy.
DEPENDS = {
    "policy": set(DATA_AGENTS),
    "verifier": {"policy"},
}


def _route(case_id: str, done: list[str], todo: list[str]) -> tuple[str, str]:
    """Model chon agent chay tiep. Moi buoc mot lan goi model.

    Coordinator khong xep san thu tu: no chi giu bang phu thuoc va tu choi lua
    chon nao chua du dau vao. `ready` la tap agent hop le tai buoc nay; model
    chon trong do. Chon sai (ten la, agent da chay, hoac thieu phu thuoc) thi
    coordinator lay phan tu dau cua `ready` va trace ghi ro la fallback.

    Vi sao van can chan: model 4.7B co the goi policy_agent khi moi chay 2 agent
    du lieu, luc do src/policy.py doc phai analysis thieu khoa va ca case chet.
    """
    ready = [n for n in todo if DEPENDS.get(n, set()) <= set(done)]
    reply = llm.extract_json(
        llm.chat(
            ROUTER_SYSTEM,
            f"case_id: {case_id}\n"
            f"da chay: {[n + '_agent' for n in done]}\n"
            f"chua chay: {[n + '_agent' for n in todo]}",
        )
    )
    pick = reply.get("next") if isinstance(reply, dict) else None
    if isinstance(pick, str):
        pick = pick.strip().removesuffix("_agent")
    if pick in ready:
        return pick, "llm_route"
    return ready[0], "fallback_dependency_order"


def _policy_slice(bundle: dict) -> dict:
    """Lat cho policy agent: dung 5 truong ma src/policy.py doc toi, khong hon.

    Policy agent khong can biet customer_id hay gia tung dong item — no chi dem
    so dong va lay order_status, order_item_id, payment_sequential de dung evidence.
    Gui ca bundle vao day la de mot agent doc duoc bang khong thuoc ve no.
    """
    order = bundle["order"]
    return {
        "order_id": bundle["order_id"],
        "order": {"order_status": order["order_status"]} if order else None,
        "items": [{"order_item_id": i["order_item_id"]} for i in bundle["items"]],
        "payments": [{"payment_sequential": p["payment_sequential"]} for p in bundle["payments"]],
        "sellers": list(bundle["sellers"]),
    }


def _slices(bundle: dict, category_translation: dict) -> dict:
    """Cat bundle thanh 4 lat. Moi agent chi thay lat cua no.

    category_translation di kem lat order_product thay vi de tool tu goi load_all():
    tool tu mo datastore la mo ca 8 index, tuc pha vo dung ranh gioi dang dung o day.
    """
    return {
        "customer": {
            "order_id": bundle["order_id"],
            "customer": bundle["customer"],
            "customer_orders": bundle["customer_orders"],
        },
        "order_product": {
            "order_id": bundle["order_id"],
            "items": bundle["items"],
            "products": bundle["products"],
            "sellers": bundle["sellers"],
            "category_translation": category_translation,
        },
        "payment": {
            "order_id": bundle["order_id"],
            "items": bundle["items"],
            "payments": bundle["payments"],
        },
        "delivery": {
            "order_id": bundle["order_id"],
            "order": bundle["order"],
            "items": bundle["items"],
            "sellers": bundle["sellers"],
        },
    }


HANDLERS = {
    "customer": customer_agent,
    "order_product": order_product_agent,
    "payment": payment_agent,
    "delivery": delivery_agent,
    "policy": policy_agent,
    "verifier": verifier_agent,
}

TASKS = {
    "customer": "analyze_customer",
    "order_product": "analyze_order_product",
    "payment": "analyze_payment",
    "delivery": "analyze_delivery",
    "policy": "apply_ec_policy_v2",
    "verifier": "verify_schema",
}


def _analysis(parts: dict) -> dict:
    """Gop 4 ket qua agent du lieu thanh dau vao cua policy agent."""
    return {
        "delivery": parts["delivery"],
        "payment": parts["payment"]["payment_reconciliation"],
        "customer": parts["customer"],
        "product": parts["order_product"]["product_context"],
    }


def _assemble(case: dict, parts: dict) -> dict:
    """Dung output cuoi tu ket qua 4 agent du lieu va ket luan cua policy agent."""
    case_id = case["case_id"]
    scope = case.get("investigation_scope") or {}
    analysis = _analysis(parts)
    ruling = parts["policy"]

    delivery = dict(analysis["delivery"])
    delivery["seller_handoff_analysis"] = _cap(delivery["seller_handoff_analysis"], MAX_SELLER_IDS)
    delivery["late_handoff_seller_ids"] = _cap(delivery["late_handoff_seller_ids"], MAX_SELLER_IDS)

    customer_context = {
        "customer_unique_id": analysis["customer"]["customer_unique_id"],
        "related_order_ids": (
            _cap(analysis["customer"]["related_order_ids"], MAX_RELATED_ORDERS)
            if scope.get("include_customer_history", True)
            else []
        ),
    }
    product_context = (
        {
            "product_ids": _cap(analysis["product"]["product_ids"], MAX_PRODUCT_IDS),
            "category_names": _cap(analysis["product"]["category_names"], MAX_CATEGORIES),
        }
        if scope.get("include_product_context", True)
        else {"product_ids": [], "category_names": []}
    )

    result = {
        "case_id": case_id,
        "case_assessment": ruling["case_assessment"],
        "affected_entities": {
            "order_ids": _cap(parts["order_product"]["order_ids"], MAX_ORDER_IDS),
            "item_ids": _cap(parts["order_product"]["item_ids"], MAX_ITEM_IDS),
            "seller_ids": _cap(parts["order_product"]["seller_ids"], MAX_SELLER_IDS),
            "payment_ids": _cap(parts["payment"]["payment_ids"], MAX_PAYMENT_IDS),
        },
        "customer_context": customer_context,
        "product_context": product_context,
        "delivery_analysis": delivery,
        "payment_reconciliation": analysis["payment"],
        "root_cause_analysis": ruling["root_cause_analysis"],
        "evidence_ids": ruling["evidence_ids"],
        "financial_resolution": ruling["financial_resolution"],
        "resolution_actions": _cap(ruling["resolution_actions"], MAX_ACTIONS),
    }
    return result


def coordinator_agent(case: dict, bundle: dict) -> dict:
    """Vong dieu phoi: moi buoc hoi model chay agent nao tiep, cho den khi het viec.

    Coordinator khong giu san mot thu tu nao. No chi giu bang phu thuoc DEPENDS
    va cat lat du lieu cho agent duoc chon. Chay het 6 agent thi dung.
    """
    case_id = case["case_id"]
    data_slices = _slices(bundle, _category_translation())
    parts: dict = {}
    built: dict = {}
    done: list[str] = []
    todo = list(ALL_AGENTS)

    while todo:
        name, source = _route(case_id, done, todo)
        bus.note(case_id, "coordinator", "route", {
            "next": name, "source": source, "done": list(done),
        })

        if name == "policy":
            payload = {"bundle": _policy_slice(bundle), "analysis": _analysis(parts)}
        elif name == "verifier":
            built["result"] = _assemble(case, parts)
            payload = {"result": built["result"]}
        else:
            payload = {"slice": data_slices[name]}

        parts[name] = bus.send(
            case_id,
            bus.envelope("coordinator", f"{name}_agent", TASKS[name], payload),
            HANDLERS[name],
        )
        done.append(name)
        todo.remove(name)

    review = parts["verifier"]
    bus.note(case_id, "verifier_agent", "review", {
        "errors": review["errors"],
        "llm_review": review["llm_review"],
    })

    return {"result": built["result"], "errors": review["errors"]}
