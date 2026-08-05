from typing import Dict, Any

class CustomerAgent:
	def __init__(self, repository):
		self.repo = repository

	def analyze(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
		claimed_order = input_case.get('customer_request', {}).get('claimed_order_id')
		result = {'customer_unique_id': None, 'related_order_ids': []}
		if not claimed_order:
			return result
		order = self.repo.get_order(claimed_order)
		if not order:
			return result
		customer_id = order.get('customer_id')
		result['customer_unique_id'] = order.get('customer_id')
		# related orders: using same customer_id (not customer_unique_id distinction in this dataset)
		customers_orders = self.repo.loader.orders
		related = customers_orders[customers_orders['customer_id'] == customer_id]['order_id'].tolist()
		related = [o for o in related if o != claimed_order]
		result['related_order_ids'] = related[:5]
		return result
