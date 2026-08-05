from typing import Dict, Any
from models.output_schema import (
	CaseOutput,
	CaseAssessment,
	AffectedEntities,
	CustomerContext,
	ProductContext,
	DeliveryAnalysis,
	PaymentReconciliation,
	RootCauseAnalysis,
	RootCauseItem,
	ResponsibleParty,
	FinancialResolution,
)


class Coordinator:
	def __init__(self, repository, customer_agent, order_agent, payment_agent, delivery_agent, policy_agent, verifier_agent):
		self.repo = repository
		self.customer_agent = customer_agent
		self.order_agent = order_agent
		self.payment_agent = payment_agent
		self.delivery_agent = delivery_agent
		self.policy_agent = policy_agent
		self.verifier_agent = verifier_agent

	def run(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
		# Step 1: domain agents
		cust = self.customer_agent.analyze(input_case)
		order_ctx = self.order_agent.analyze(input_case)
		items = order_ctx.get('items', [])
		payments = self.payment_agent.analyze(order_ctx.get('order', {}).get('order_id') if order_ctx.get('order') else None, items)
		delivery = self.delivery_agent.analyze(order_ctx.get('order'), items)

		# policy
		policy = self.policy_agent.decide(order_ctx, payments, delivery)

		case_id = input_case.get('case_id')
		pids = list({it.get('product_id') for it in items if it.get('product_id')})
		products_info = self.repo.get_products(pids) if pids else []
		# Note: we need to preserve order somewhat or just use list
		categories = list({p.get('product_category_name') for p in products_info if isinstance(p.get('product_category_name'), str)})

		secondary_issues = []
		if len(items) >= 2:
			secondary_issues.append("multi_item_order")
		sellers_set = set(it.get('seller_id') for it in items if it.get('seller_id'))
		if len(sellers_set) >= 2:
			secondary_issues.append("multi_seller_order")
		if len(payments.get('payment_types', [])) >= 2 or len(payments.get('payment_ids', [])) >= 2:
			secondary_issues.append("split_payment")
		if len(cust.get('related_order_ids', [])) > 0:
			secondary_issues.append("repeat_customer")
		if len(categories) >= 2:
			secondary_issues.append("multiple_categories")

		assessment = CaseAssessment(
			primary_issue=policy.get('primary_issue'),
			secondary_issues=secondary_issues,
			case_status='action_required' if policy.get('refund') and policy.get('refund') > 0 else 'no_action',
			confidence=policy.get('confidence', 0.0),
		)

		affected = AffectedEntities(
			order_ids=[order_ctx.get('order', {}).get('order_id')] if order_ctx.get('order') else [],
			item_ids=[f"{order_ctx.get('order', {}).get('order_id')}:{it.get('order_item_id')}" for it in items][:5],
			seller_ids=list(sellers_set)[:3],
			payment_ids=payments.get('payment_ids', [])[:5],
		)

		customer_ctx = CustomerContext(customer_unique_id=cust.get('customer_unique_id'), related_order_ids=cust.get('related_order_ids', []))
		product_ctx = ProductContext(product_ids=pids[:5], category_names=categories[:5])

		delivery_analysis = DeliveryAnalysis(**delivery)
		payment_recon = PaymentReconciliation(
			currency=payments.get('currency', 'BRL'),
			item_total_brl=payments.get('item_total_brl'),
			freight_total_brl=payments.get('freight_total_brl'),
			expected_total_brl=payments.get('expected_total_brl'),
			payment_total_brl=payments.get('payment_total_brl'),
			difference_brl=payments.get('difference_brl'),
			reconciled=payments.get('reconciled'),
			payment_types=payments.get('payment_types', []),
		)

		rc_items = []
		for idx, rc in enumerate(policy.get('responsible', [])[:3], start=1):
			rc_items.append(ResponsibleParty(party_type=rc.get('party_type'), party_id=rc.get('party_id')))

		root = RootCauseAnalysis(
			ranked_causes=[RootCauseItem(cause_code=policy.get('cause_code'), rank=1)] if policy.get('cause_code') else [], 
			responsible_parties=rc_items
		)

		financial = FinancialResolution(currency='BRL', recommended_refund_brl=policy.get('refund'))

		actions = list(policy.get('actions', []))
		if policy.get('refund') and policy.get('refund') > 0:
			if 'verify_refund_completion' not in actions:
				actions.append('verify_refund_completion')
		if 'multi_seller_order' in secondary_issues and 'coordinate_multi_seller_case' not in actions:
			actions.append('coordinate_multi_seller_case')
		if 'split_payment' in secondary_issues and policy.get('primary_issue') != 'valid_split_payment' and 'verify_payment_allocation' not in actions:
			actions.append('verify_payment_allocation')

		out = CaseOutput(
			case_id=case_id,
			case_assessment=assessment,
			affected_entities=affected,
			customer_context=customer_ctx,
			product_context=product_ctx,
			delivery_analysis=delivery_analysis,
			payment_reconciliation=payment_recon,
			root_cause_analysis=root,
			evidence_ids=policy.get('evidence', [])[:20],
			financial_resolution=financial,
			resolution_actions=actions[:5],
		)

		# verifier
		ok, reason = self.verifier_agent.verify(out.dict())
		if not ok:
			raise ValueError(f"Verifier rejected output: {reason}")

		return out.dict()
