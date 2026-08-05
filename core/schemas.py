"""Pydantic schema cho output theo README mục 6, bao gồm giới hạn mảng (mục 6, dòng "Giới hạn")."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

PrimaryIssue = Literal[
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
]

SecondaryIssue = Literal[
    "multi_item_order",
    "multi_seller_order",
    "split_payment",
    "repeat_customer",
    "multiple_categories",
]

CaseStatus = Literal["action_required", "no_action"]

CauseCode = Literal[
    "SELLER_HANDOFF_AFTER_LIMIT",
    "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT",
    "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED",
    "DELIVERY_WITHIN_ESTIMATE",
]

PartyType = Literal["platform", "seller", "logistics_provider"]

ResolutionAction = Literal[
    "issue_full_refund",
    "refund_freight",
    "explain_valid_split_payment",
    "reject_late_refund",
    "review_seller_handoff",
    "review_carrier_delay",
    "verify_refund_completion",
    "coordinate_multi_seller_case",
    "verify_payment_allocation",
]


class CaseAssessment(BaseModel):
    primary_issue: PrimaryIssue
    secondary_issues: list[SecondaryIssue] = Field(default_factory=list, max_length=5)
    case_status: CaseStatus
    confidence: float = Field(ge=0.0, le=1.0)


class AffectedEntities(BaseModel):
    order_ids: list[str] = Field(default_factory=list, max_length=5)
    item_ids: list[str] = Field(default_factory=list, max_length=5)
    seller_ids: list[str] = Field(default_factory=list, max_length=3)
    payment_ids: list[str] = Field(default_factory=list, max_length=5)


class CustomerContext(BaseModel):
    customer_unique_id: str
    related_order_ids: list[str] = Field(default_factory=list, max_length=5)


class ProductContext(BaseModel):
    product_ids: list[str] = Field(default_factory=list, max_length=5)
    category_names: list[str] = Field(default_factory=list, max_length=5)


class SellerHandoffAnalysis(BaseModel):
    seller_id: str
    shipping_limit_at: Optional[str] = None
    handoff_variance_hours: Optional[float] = None
    late_handoff: bool


class DeliveryAnalysis(BaseModel):
    delivered_at: Optional[str] = None
    estimated_delivery_at: Optional[str] = None
    carrier_handoff_at: Optional[str] = None
    delivery_variance_hours: Optional[float] = None
    seller_handoff_analysis: list[SellerHandoffAnalysis] = Field(default_factory=list)
    late_handoff_seller_ids: list[str] = Field(default_factory=list)


class PaymentReconciliation(BaseModel):
    currency: Literal["BRL"] = "BRL"
    item_total_brl: Optional[float] = None
    freight_total_brl: Optional[float] = None
    expected_total_brl: Optional[float] = None
    payment_total_brl: Optional[float] = None
    difference_brl: Optional[float] = None
    reconciled: Optional[bool] = None
    payment_types: list[str] = Field(default_factory=list)


class RankedCause(BaseModel):
    cause_code: CauseCode
    rank: int


class ResponsibleParty(BaseModel):
    party_type: PartyType
    party_id: str


class RootCauseAnalysis(BaseModel):
    ranked_causes: list[RankedCause] = Field(default_factory=list, max_length=3)
    responsible_parties: list[ResponsibleParty] = Field(default_factory=list, max_length=3)


class FinancialResolution(BaseModel):
    currency: Literal["BRL"] = "BRL"
    recommended_refund_brl: float


class CaseOutput(BaseModel):
    case_id: str
    case_assessment: CaseAssessment
    affected_entities: AffectedEntities
    customer_context: CustomerContext
    product_context: ProductContext
    delivery_analysis: DeliveryAnalysis
    payment_reconciliation: PaymentReconciliation
    root_cause_analysis: RootCauseAnalysis
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    financial_resolution: FinancialResolution
    resolution_actions: list[ResolutionAction] = Field(default_factory=list, max_length=5)
