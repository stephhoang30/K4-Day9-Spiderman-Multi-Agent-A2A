"""Load 9 CSV Olist một lần và cung cấp lookup theo order_id/customer_id.

Đây là lớp truy cập dữ liệu dùng chung cho mọi agent; mỗi agent chỉ được gọi
các phương thức tương ứng với domain của mình (least-privilege access, xem
architecture.md).
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class DataStore:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.orders = pd.read_csv(data_dir / "olist_orders_dataset.csv")
        self.customers = pd.read_csv(data_dir / "olist_customers_dataset.csv")
        self.order_items = pd.read_csv(data_dir / "olist_order_items_dataset.csv")
        self.order_payments = pd.read_csv(data_dir / "olist_order_payments_dataset.csv")
        self.products = pd.read_csv(data_dir / "olist_products_dataset.csv")
        self.sellers = pd.read_csv(data_dir / "olist_sellers_dataset.csv")

        self._orders_by_id = self.orders.set_index("order_id", drop=False)
        self._customers_by_id = self.customers.set_index("customer_id", drop=False)

        # Tránh groupby(...) + dict-comprehension tạo ~100K DataFrame con riêng lẻ
        # (cực chậm, ~25s+ với dữ liệu Olist) — to_dict("records") 1 lần rồi gom
        # bằng Python thuần nhanh hơn nhiều bậc.
        #
        # KHÔNG sort_values(...) lại theo order_item_id/payment_sequential: README
        # yêu cầu "giữ thứ tự ổn định theo dữ liệu nguồn" — với payment, 9/50 case
        # thật có thứ tự dòng trong CSV KHÁC thứ tự payment_sequential tăng dần
        # (VD payment_sequential xuất hiện theo thứ tự [2, 1] trong file), nên phải
        # giữ nguyên thứ tự dòng gốc thay vì tự resort.
        self._items_by_order: dict[str, list[dict]] = {}
        for row in self.order_items.to_dict("records"):
            self._items_by_order.setdefault(row["order_id"], []).append(row)

        self._payments_by_order: dict[str, list[dict]] = {}
        for row in self.order_payments.to_dict("records"):
            self._payments_by_order.setdefault(row["order_id"], []).append(row)

        self._products_by_id = self.products.set_index("product_id", drop=False)
        self._sellers_by_id = self.sellers.set_index("seller_id", drop=False)

    def get_order(self, order_id: str) -> dict | None:
        if order_id not in self._orders_by_id.index:
            return None
        return self._orders_by_id.loc[order_id].to_dict()

    def get_customer(self, customer_id: str) -> dict | None:
        if customer_id not in self._customers_by_id.index:
            return None
        return self._customers_by_id.loc[customer_id].to_dict()

    def get_items(self, order_id: str) -> list[dict]:
        return self._items_by_order.get(order_id, [])

    def get_payments(self, order_id: str) -> list[dict]:
        return self._payments_by_order.get(order_id, [])

    def get_product(self, product_id: str) -> dict | None:
        if product_id not in self._products_by_id.index:
            return None
        return self._products_by_id.loc[product_id].to_dict()

    def get_seller(self, seller_id: str) -> dict | None:
        if seller_id not in self._sellers_by_id.index:
            return None
        return self._sellers_by_id.loc[seller_id].to_dict()

    def get_related_order_ids(self, customer_unique_id: str, exclude_order_id: str) -> list[str]:
        """Các order khác của cùng customer_unique_id, sắp xếp theo purchase timestamp."""
        cust_ids = self._customers_by_id[
            self._customers_by_id["customer_unique_id"] == customer_unique_id
        ]["customer_id"]
        orders = self.orders[
            self.orders["customer_id"].isin(cust_ids) & (self.orders["order_id"] != exclude_order_id)
        ].sort_values("order_purchase_timestamp")
        return orders["order_id"].tolist()


_store: DataStore | None = None


def get_store() -> DataStore:
    global _store
    if _store is None:
        _store = DataStore()
    return _store
