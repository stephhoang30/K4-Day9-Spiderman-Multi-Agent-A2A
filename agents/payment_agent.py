from typing import Dict, Any
import math
import json
import config

try:
	from services.llm import generate_completion
except Exception:
	generate_completion = None


class PaymentAgent:
	def __init__(self, repository, use_llm: bool = True):
		self.repo = repository
		self.use_llm = use_llm and getattr(config, 'MODEL_NAME', None) is not None and generate_completion is not None

	def _deterministic(self, order_id: str, items: list) -> Dict[str, Any]:
		payments = self.repo.get_payments(order_id)
		item_total = None
		freight_total = None
		if items:
			item_total = sum((float(i.get('price') or 0) for i in items))
			freight_total = sum((float(i.get('freight_value') or 0) for i in items))
		expected = None
		if item_total is not None and freight_total is not None:
			expected = round(item_total + freight_total, 2)
		payment_total = sum((float(p.get('payment_value') or 0) for p in payments)) if payments else None
		diff = None
		reconciled = None
		if payment_total is not None and expected is not None:
			diff = round(payment_total - expected, 2)
			reconciled = abs(diff) <= 0.10
		payment_types = [p.get('payment_type') for p in payments]
		return {
			'currency': 'BRL',
			'item_total_brl': item_total,
			'freight_total_brl': freight_total,
			'expected_total_brl': expected,
			'payment_total_brl': payment_total,
			'difference_brl': diff,
			'reconciled': reconciled,
			'payment_types': payment_types,
			'payment_ids': [f"{order_id}:{p.get('payment_sequential')}" for p in payments if p.get('payment_sequential') is not None]
		}

	def analyze(self, order_id: str, items: list) -> Dict[str, Any]:
		if not self.use_llm:
			return self._deterministic(order_id, items)

		prompt = {'task': 'payment_reconciliation', 'order_id': order_id, 'items': items}
		try:
			raw = generate_completion(json.dumps(prompt), model=getattr(config, 'MODEL_NAME', None))
			parsed = json.loads(raw)
			if 'payment_total_brl' in parsed:
				return parsed
		except Exception:
			pass
		return self._deterministic(order_id, items)

