from typing import Optional, List
from services.data_loader import DataLoader
import pandas as pd


class Repository:
	def __init__(self, loader: DataLoader):
		self.loader = loader

	def get_order(self, order_id: str) -> Optional[dict]:
		df = self.loader.orders
		row = df[df['order_id'] == order_id]
		if row.empty:
			return None
		return row.iloc[0].to_dict()

	def get_order_items(self, order_id: str) -> List[dict]:
		df = self.loader.order_items
		rows = df[df['order_id'] == order_id]
		return rows.to_dict(orient='records')

	def get_payments(self, order_id: str) -> List[dict]:
		df = self.loader.order_payments
		rows = df[df['order_id'] == order_id]
		return rows.to_dict(orient='records')

	def get_customer(self, customer_id: str) -> Optional[dict]:
		df = self.loader.customers
		row = df[df['customer_id'] == customer_id]
		if row.empty:
			return None
		return row.iloc[0].to_dict()

	def get_products(self, product_ids: List[str]) -> List[dict]:
		df = self.loader.products
		rows = df[df['product_id'].isin(product_ids)]
		return rows.to_dict(orient='records')

