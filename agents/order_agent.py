from typing import Dict, Any
import json
import config

try:
	from services.llm import generate_completion
except Exception:
	generate_completion = None


class OrderAgent:
	def __init__(self, repository, use_llm: bool = True):
		self.repo = repository
		self.use_llm = use_llm and getattr(config, 'MODEL_NAME', None) is not None and generate_completion is not None

	def _deterministic(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
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

	def analyze(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
		if not self.use_llm:
			return self._deterministic(input_case)

		prompt = {'task': 'order_context', 'input_case': input_case}
		try:
			raw = generate_completion(json.dumps(prompt), model=getattr(config, 'MODEL_NAME', None))
			parsed = json.loads(raw)
			if 'order' in parsed and 'items' in parsed:
				return parsed
		except Exception:
			pass
		return self._deterministic(input_case)
