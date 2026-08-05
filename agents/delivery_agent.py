
from typing import Dict, Any, List
from datetime import datetime
import json
import config

try:
	from services.llm import generate_completion
except Exception:
	generate_completion = None


def parse_dt(v):
	if not v or (isinstance(v, float) and v != v):
		return None
	try:
		return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
	except Exception:
		return None


class DeliveryAgent:
	def __init__(self, repository, use_llm: bool = True):
		self.repo = repository
		self.use_llm = use_llm and getattr(config, 'MODEL_NAME', None) is not None and generate_completion is not None

	def _deterministic(self, order: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
		if not order:
			return {
				"delivered_at": None,
				"estimated_delivery_at": None,
				"carrier_handoff_at": None,
				"delivery_variance_hours": None,
				"seller_handoff_analysis": [],
				"late_handoff_seller_ids": [],
			}

		delivered = parse_dt(order.get("order_delivered_customer_date"))
		estimated = parse_dt(order.get("order_estimated_delivery_date"))
		delivery_variance = None
		if delivered and estimated:
			delta = delivered - estimated
			delivery_variance = round(delta.total_seconds() / 3600.0, 2)

		seller_limits = {}
		for it in items:
			sid = it.get("seller_id")
			limit_str = it.get("shipping_limit_date")
			limit_dt = parse_dt(limit_str)
			if sid and limit_dt:
				if sid not in seller_limits or limit_dt < seller_limits[sid][1]:
					seller_limits[sid] = (limit_str, limit_dt)

		seller_analysis = []
		late_ids = []
		for sid, (limit_str, ship_limit) in seller_limits.items():
			carrier_handoff = parse_dt(order.get("order_delivered_carrier_date"))
			handoff_variance = None
			late = False
			if carrier_handoff and ship_limit:
				hv = carrier_handoff - ship_limit
				handoff_variance = round(hv.total_seconds() / 3600.0, 2)
				late = handoff_variance > 0
			seller_analysis.append(
				{
					"seller_id": sid,
					"shipping_limit_at": limit_str,
					"handoff_variance_hours": handoff_variance,
					"late_handoff": late,
				}
			)
			if late:
				late_ids.append(sid)

		def norm_str(x):
			return x if isinstance(x, str) else None

		return {
			"delivered_at": norm_str(order.get("order_delivered_customer_date")),
			"estimated_delivery_at": norm_str(order.get("order_estimated_delivery_date")),
			"carrier_handoff_at": norm_str(order.get("order_delivered_carrier_date")),
			"delivery_variance_hours": delivery_variance,
			"seller_handoff_analysis": seller_analysis,
			"late_handoff_seller_ids": list(dict.fromkeys(late_ids))[:3],
		}

	def analyze(self, order: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
		if not self.use_llm:
			return self._deterministic(order, items)

		prompt = {"task": "delivery_analysis", "order": order, "items": items}
		try:
			raw = generate_completion(json.dumps(prompt), model=getattr(config, "MODEL_NAME", None))
			parsed = json.loads(raw)
			if "delivery_variance_hours" in parsed:
				return parsed
		except Exception:
			pass
		return self._deterministic(order, items)


