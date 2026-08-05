from typing import Dict, Any
import json
import config

try:
	from services.llm import generate_completion
except Exception:
	generate_completion = None


class CustomerAgent:
	def __init__(self, repository, use_llm: bool = True):
		self.repo = repository
		self.use_llm = use_llm and getattr(config, 'MODEL_NAME', None) is not None and generate_completion is not None

	def _deterministic(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
		claimed_order = input_case.get('customer_request', {}).get('claimed_order_id')
		result = {'customer_unique_id': None, 'related_order_ids': []}
		if not claimed_order:
			return result
		order = self.repo.get_order(claimed_order)
		if not order:
			return result
		customer_id = order.get('customer_id')
		result['customer_unique_id'] = order.get('customer_id')
		customers_orders = self.repo.loader.orders
		related = customers_orders[customers_orders['customer_id'] == customer_id]['order_id'].tolist()
		related = [o for o in related if o != claimed_order]
		result['related_order_ids'] = related[:5]
		return result

	def analyze(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
		if not self.use_llm:
			return self._deterministic(input_case)

		prompt = {'task': 'customer_context', 'input_case': input_case}
		try:
			raw = generate_completion(json.dumps(prompt), model=getattr(config, 'MODEL_NAME', None))
			parsed = json.loads(raw)
			if 'customer_unique_id' in parsed and 'related_order_ids' in parsed:
				return parsed
		except Exception:
			pass
		return self._deterministic(input_case)
