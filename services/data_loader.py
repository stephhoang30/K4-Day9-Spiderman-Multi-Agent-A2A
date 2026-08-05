import numpy as np
import pandas as pd

from pathlib import Path
import pandas as pd


class DataLoader:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._tables = {}

    def load(self, table_name: str) -> pd.DataFrame:
        if table_name not in self._tables:
            path = self.data_dir / f"{table_name}.csv"
            self._tables[table_name] = pd.read_csv(path)
        return self._tables[table_name]

    @property
    def orders(self):
        return self.load("olist_orders_dataset")

    @property
    def customers(self):
        return self.load("olist_customers_dataset")

    @property
    def order_items(self):
        return self.load("olist_order_items_dataset")

    @property
    def order_payments(self):
        return self.load("olist_order_payments_dataset")

    @property
    def order_reviews(self):
        return self.load("olist_order_reviews_dataset")

    @property
    def products(self):
        return self.load("olist_products_dataset")

    @property
    def sellers(self):
        return self.load("olist_sellers_dataset")

    @property
    def geolocation(self):
        return self.load("olist_geolocation_dataset")