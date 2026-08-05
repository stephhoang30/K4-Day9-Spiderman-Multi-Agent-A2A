from typing import Dict, Any

class OrderAgent:
	def __init__(self, repository):
		self.repo = repository

	def analyze(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
		claimed_order = input_case.get('customer_request', {}).get('claimed_order_id')
		out = {'order': None, 'items': [], 'sellers': []}
		if not claimed_order:
			return out
		order = self.repo.get_order(claimed_order)
		if not order:
			return out
		items = self.repo.get_order_items(claimed_order)
		sellers = list({it.get('seller_id') for it in items if it.get('seller_id')})
		out['order'] = order
		out['items'] = items
		out['sellers'] = sellers[:3]
		return out
