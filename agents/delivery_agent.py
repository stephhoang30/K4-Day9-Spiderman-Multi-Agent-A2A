from typing import Dict, Any, List
from datetime import datetime


def parse_dt(v):
	if not v or (isinstance(v, float) and v != v):
		return None
	try:
		return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
	except Exception:
		return None


class DeliveryAgent:
	def __init__(self, repository):
		self.repo = repository

	def analyze(self, order: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
		if not order:
			return {
				'delivered_at': None,
				'estimated_delivery_at': None,
				'carrier_handoff_at': None,
				'delivery_variance_hours': None,
				'seller_handoff_analysis': [],
				'late_handoff_seller_ids': []
			}
		delivered = parse_dt(order.get('order_delivered_customer_date'))
		estimated = parse_dt(order.get('order_estimated_delivery_date'))
		carrier = parse_dt(order.get('order_delivered_carrier_date'))
		delivery_variance = None
		if delivered and estimated:
			delta = delivered - estimated
			delivery_variance = round(delta.total_seconds() / 3600.0, 2)

		# seller handoff: use shipping_limit_date from items
		seller_analysis = []
		late_ids = []
		for it in items:
			ship_limit = parse_dt(it.get('shipping_limit_date'))
			carrier_handoff = parse_dt(order.get('order_delivered_carrier_date'))
			handoff_variance = None
			late = False
			if carrier_handoff and ship_limit:
				hv = carrier_handoff - ship_limit
				handoff_variance = round(hv.total_seconds() / 3600.0, 2)
				late = handoff_variance > 0
			seller_analysis.append({
				'seller_id': it.get('seller_id'),
				'shipping_limit_at': it.get('shipping_limit_date'),
				'handoff_variance_hours': handoff_variance,
				'late_handoff': late
			})
			if late:
				late_ids.append(it.get('seller_id'))

		def norm_str(x):
			return x if isinstance(x, str) else None

		return {
			'delivered_at': norm_str(order.get('order_delivered_customer_date')),
			'estimated_delivery_at': norm_str(order.get('order_estimated_delivery_date')),
			'carrier_handoff_at': norm_str(order.get('order_delivered_carrier_date')),
			'delivery_variance_hours': delivery_variance,
			'seller_handoff_analysis': [
				{
					'seller_id': s.get('seller_id'),
					'shipping_limit_at': norm_str(s.get('shipping_limit_at')) if isinstance(s, dict) and s.get('shipping_limit_at') is not None else norm_str(s.get('shipping_limit_at') if isinstance(s, dict) else None)
				} for s in []
			] if False else seller_analysis,
			'late_handoff_seller_ids': list(dict.fromkeys(late_ids))[:3]
		}

