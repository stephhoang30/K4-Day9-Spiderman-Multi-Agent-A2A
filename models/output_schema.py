from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CaseAssessment(BaseModel):
	primary_issue: Optional[str]
	secondary_issues: List[str] = []
	case_status: str = "no_action"
	confidence: float = 0.0


class AffectedEntities(BaseModel):
	order_ids: List[str] = []
	item_ids: List[str] = []
	seller_ids: List[str] = []
	payment_ids: List[str] = []


class CustomerContext(BaseModel):
	customer_unique_id: Optional[str]
	related_order_ids: List[str] = []


class ProductContext(BaseModel):
	product_ids: List[str] = []
	category_names: List[str] = []


class SellerHandoff(BaseModel):
	seller_id: str
	shipping_limit_at: Optional[str]
	handoff_variance_hours: Optional[float]
	late_handoff: bool = False


class DeliveryAnalysis(BaseModel):
	delivered_at: Optional[str]
	estimated_delivery_at: Optional[str]
	carrier_handoff_at: Optional[str]
	delivery_variance_hours: Optional[float]
	seller_handoff_analysis: List[SellerHandoff] = []
	late_handoff_seller_ids: List[str] = []


class PaymentReconciliation(BaseModel):
	currency: str = "BRL"
	item_total_brl: Optional[float]
	freight_total_brl: Optional[float]
	expected_total_brl: Optional[float]
	payment_total_brl: Optional[float]
	difference_brl: Optional[float]
	reconciled: Optional[bool]
	payment_types: List[str] = []


class RootCauseItem(BaseModel):
	cause_code: str
	rank: int


class ResponsibleParty(BaseModel):
	party_type: str
	party_id: str


class RootCauseAnalysis(BaseModel):
	ranked_causes: List[RootCauseItem] = []
	responsible_parties: List[ResponsibleParty] = []


class FinancialResolution(BaseModel):
	currency: str = "BRL"
	recommended_refund_brl: Optional[float]


class CaseOutput(BaseModel):
	case_id: str
	case_assessment: CaseAssessment
	affected_entities: AffectedEntities
	customer_context: CustomerContext
	product_context: ProductContext
	delivery_analysis: DeliveryAnalysis
	payment_reconciliation: PaymentReconciliation
	root_cause_analysis: RootCauseAnalysis
	evidence_ids: List[str] = []
	financial_resolution: FinancialResolution
	resolution_actions: List[str] = []

	def to_json(self) -> str:
		return self.json(indent=2, ensure_ascii=False)
