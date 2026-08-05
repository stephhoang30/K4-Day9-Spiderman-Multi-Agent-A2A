from typing import Dict, Any, List
from typing import Dict, Any, List
import json
import config

try:
	from services.llm import generate_completion
except Exception:
	generate_completion = None


class PolicyAgent:
	def __init__(self, use_llm: bool = True):
		self.use_llm = use_llm and getattr(config, 'MODEL_NAME', None) is not None and generate_completion is not None

	def _deterministic(self, order_ctx: Dict[str, Any], payment_ctx: Dict[str, Any], delivery_ctx: Dict[str, Any]) -> Dict[str, Any]:
		# original deterministic logic
		primary = None
		actions: List[str] = []
		refund_amount = None
		responsible = []
		evidence = []

		order = order_ctx.get('order') if order_ctx else None
		if not order:
			return {'primary_issue': None, 'actions': [], 'refund': None, 'responsible': [], 'evidence': [], 'confidence': 0.0, 'cause_code': None}

		payment_total = payment_ctx.get('payment_total_brl')
		order_status = order.get('order_status')
		dv = delivery_ctx.get('delivery_variance_hours')
		late_sellers = delivery_ctx.get('late_handoff_seller_ids') or []

		if order_status == 'canceled' and (payment_total or 0) > 0:
			primary = 'canceled_order_paid'
			cause_code = 'ORDER_CANCELED_AFTER_PAYMENT'
			refund_amount = payment_total
			actions = ['issue_full_refund']
			responsible = [{'party_type': 'platform', 'party_id': 'OLIST_PLATFORM'}]
		elif order_status == 'unavailable' and (payment_total or 0) > 0:
			primary = 'unavailable_order_paid'
			cause_code = 'ORDER_UNAVAILABLE_AFTER_PAYMENT'
			refund_amount = payment_total
			actions = ['issue_full_refund']
			responsible = [{'party_type': 'platform', 'party_id': 'OLIST_PLATFORM'}]
		elif dv is not None and dv > 0:
			if late_sellers:
				primary = 'late_delivery_seller'
				cause_code = 'SELLER_HANDOFF_AFTER_LIMIT'
				refund_amount = payment_ctx.get('freight_total_brl')
				actions = ['refund_freight', 'review_seller_handoff']
				responsible = [{'party_type': 'seller', 'party_id': sid} for sid in late_sellers]
			else:
				primary = 'late_delivery_logistics'
				cause_code = 'CARRIER_DELIVERED_AFTER_ESTIMATE'
				refund_amount = payment_ctx.get('freight_total_brl')
				actions = ['refund_freight', 'review_carrier_delay']
				responsible = [{'party_type': 'logistics_provider', 'party_id': 'LOGISTICS_PROVIDER'}]
		elif len(payment_ctx.get('payment_ids', [])) >= 2 and payment_ctx.get('reconciled'):
			primary = 'valid_split_payment'
			cause_code = 'MULTIPLE_PAYMENTS_RECONCILED'
			actions = ['explain_valid_split_payment']
			refund_amount = 0
		else:
			primary = 'unsupported_late_claim'
			cause_code = 'DELIVERY_WITHIN_ESTIMATE'
			actions = ['reject_late_refund']
			refund_amount = 0

		oid = order.get('order_id')
		if oid:
			evidence.append(f'order:{oid}')
		for it in order_ctx.get('items', [])[:5]:
			evidence.append(f"item:{oid}:{it.get('order_item_id')}")
		for pid in payment_ctx.get('payment_ids', [])[:5]:
			evidence.append(pid)
		for s in responsible[:3]:
			evidence.append(f"seller:{s.get('party_id')}")
		if cause_code:
			evidence.append(f'policy:{cause_code}')


		confidence = 0.9 if primary and primary != 'unsupported_late_claim' else 0.6

		return {
			'primary_issue': primary,
			'actions': actions,
			'refund': refund_amount,
			'responsible': responsible,
			'evidence': evidence,
			'confidence': confidence,
			'cause_code': cause_code,
		}

	def decide(self, order_ctx: Dict[str, Any], payment_ctx: Dict[str, Any], delivery_ctx: Dict[str, Any]) -> Dict[str, Any]:
		if not self.use_llm:
			return self._deterministic(order_ctx, payment_ctx, delivery_ctx)

		# Build a concise prompt and ask the LLM to return a JSON object with required fields.
		prompt = {
			'instruction': 'Apply EC_POLICY_V2 and return JSON with keys: primary_issue, actions (list), refund (number), responsible (list of {party_type,party_id}), evidence (list of strings), confidence (0-1). Use only evidence ids derivable from data.' ,
			'order': order_ctx.get('order'),
			'items': order_ctx.get('items'),
			'payments': {k: v for k, v in payment_ctx.items() if k != 'payment_ids'},
			'delivery': delivery_ctx,
		}

		raw = generate_completion(json.dumps(prompt), model=getattr(config, 'MODEL_NAME', None), temperature=getattr(config, 'TEMPERATURE', 0.0), max_tokens=getattr(config, 'MAX_TOKENS', 512))
		try:
			parsed = json.loads(raw)
			# ensure required fields exist
			for k in ['primary_issue', 'actions', 'refund', 'responsible', 'evidence', 'confidence']:
				if k not in parsed:
					return self._deterministic(order_ctx, payment_ctx, delivery_ctx)
			return parsed
		except Exception:
			return self._deterministic(order_ctx, payment_ctx, delivery_ctx)

