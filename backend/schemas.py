from pydantic import BaseModel
from typing import Optional, Any, Dict


class OrderCreate(BaseModel):
    description: str
    operator: Optional[str] = "System"


class AdvanceRequest(BaseModel):
    operator: Optional[str] = "System"
    note: Optional[str] = ""
    expected_stage: Optional[str] = None

class ReworkRequest(BaseModel):
    rework_qty: int
    target_stage: str
    operator: Optional[str] = "System"
    note: Optional[str] = ""
    expected_stage: Optional[str] = None


class IssueRequest(BaseModel):
    issue: str
    operator: Optional[str] = "System"


class BatchResponse(BaseModel):
    id: int
    order_code: str
    product_name: str
    quantity: int
    current_stage: str
    status: str
    priority: int
    specs: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}
