from typing import Dict, Any

class VerifierAgent:
	def __init__(self):
		pass

	def verify(self, output: Dict[str, Any]) -> (bool, str):
		# Basic checks according to README limits
		try:
			aids = output.get('affected_entities', {})
			if len(aids.get('order_ids', [])) > 5:
				return False, 'too_many_order_ids'
			if len(aids.get('item_ids', [])) > 5:
				return False, 'too_many_item_ids'
			if len(aids.get('seller_ids', [])) > 3:
				return False, 'too_many_seller_ids'
			if len(output.get('evidence_ids', [])) > 20:
				return False, 'too_many_evidence'
			conf = output.get('case_assessment', {}).get('confidence')
			if conf is None or conf < 0 or conf > 1:
				return False, 'invalid_confidence'
		except Exception as e:
			return False, f'verifier_exception:{e}'
		return True, 'ok'
