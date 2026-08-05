from typing import Optional
from pydantic import BaseModel


class CustomerRequest(BaseModel):
	language: Optional[str]
	message: Optional[str]
	claimed_order_id: Optional[str]


class InvestigationScope(BaseModel):
	include_customer_history: Optional[bool] = True
	include_product_context: Optional[bool] = True


class InputCase(BaseModel):
	case_id: str
	customer_request: CustomerRequest
	investigation_scope: InvestigationScope
	policy_version: Optional[str] = "EC_POLICY_V2"

	@classmethod
	def load_json(cls, data: dict) -> "InputCase":
		return cls.parse_obj(data)

