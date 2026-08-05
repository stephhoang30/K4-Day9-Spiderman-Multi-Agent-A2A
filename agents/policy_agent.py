from typing import Dict, Any, List

class PolicyAgent:
	def __init__(self):
		pass

	def decide(self, order_ctx: Dict[str, Any], payment_ctx: Dict[str, Any], delivery_ctx: Dict[str, Any]) -> Dict[str, Any]:
		# Evaluate primary issues following README order
		primary = None
		actions: List[str] = []
		refund_amount = None
		responsible = []
		evidence = []

		order = order_ctx.get('order') if order_ctx else None
		if not order:
			primary = None
			return {'primary_issue': primary, 'actions': actions, 'refund': None, 'responsible': responsible, 'evidence': evidence, 'confidence': 0.0}

		payment_total = payment_ctx.get('payment_total_brl')
		expected_total = payment_ctx.get('expected_total_brl')

		# canceled or unavailable
		if order.get('order_status') in ('canceled',) and (payment_total or 0) > 0:
			if order.get('order_status') == 'canceled':
				primary = 'canceled_order_paid'
			else:
				primary = 'unavailable_order_paid'
			refund_amount = payment_total
			actions = ['issue_full_refund']
			responsible = [{'party_type': 'platform', 'party_id': 'OLIST_PLATFORM'}]
		else:
			# late delivery
			dv = delivery_ctx.get('delivery_variance_hours')
			late_sellers = delivery_ctx.get('late_handoff_seller_ids') or []
			if dv is not None and dv > 0:
				if late_sellers:
					primary = 'late_delivery_seller'
					refund_amount = payment_ctx.get('freight_total_brl')
					actions = ['refund_freight', 'review_seller_handoff']
					responsible = [{'party_type': 'seller', 'party_id': sid} for sid in late_sellers]
				else:
					primary = 'late_delivery_logistics'
					refund_amount = payment_ctx.get('freight_total_brl')
					actions = ['refund_freight', 'review_carrier_delay']
					responsible = [{'party_type': 'logistics_provider', 'party_id': 'LOGISTICS_PROVIDER'}]
			else:
				# split payment
				payments = payment_ctx.get('payment_types') or []
				if len(payment_ctx.get('payment_ids', [])) >= 2 and payment_ctx.get('reconciled'):
					primary = 'valid_split_payment'
					actions = ['explain_valid_split_payment']
					refund_amount = 0
				else:
					primary = 'unsupported_late_claim'
					actions = ['reject_late_refund']
					refund_amount = 0

		# evidence simple: order, items, payments, sellers
		oid = order.get('order_id')
		if oid:
			evidence.append(f'order:{oid}')
		for it in order_ctx.get('items', [])[:5]:
			evidence.append(f"item:{oid}:{it.get('order_item_id')}")
		for pid in payment_ctx.get('payment_ids', [])[:5]:
			evidence.append(pid)
		for s in responsible[:3]:
			evidence.append(f"seller:{s.get('party_id')}")

		confidence = 0.9 if primary and primary != 'unsupported_late_claim' else 0.6

		return {
			'primary_issue': primary,
			'actions': actions,
			'refund': refund_amount,
			'responsible': responsible,
			'evidence': evidence,
			'confidence': confidence,
		}

