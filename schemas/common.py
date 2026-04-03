from pydantic import BaseModel
from typing import TypeVar, Generic, Optional

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


# ---------------------------------------------------------------------------
# Payment schemas (HitPay PayNow)
# ---------------------------------------------------------------------------

class PaymentCreateRequest(BaseModel):
    amount: float
    description: str = "Garden Roots Order"
    order_id: int
    payment_method: Optional[str] = "paynow"
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


class PaymentCreateResponse(BaseModel):
    payment_intent_id: str    # HitPay payment_request_id
    payment_url: str          # HitPay hosted checkout URL — redirect customer here
    status: str
    amount: float
    currency: str = "SGD"


class PaymentStatusResponse(BaseModel):
    status: str
    payment_intent_id: str
    amount: Optional[float] = None
    currency: Optional[str] = "SGD"


class PaymentConfirmResponse(BaseModel):
    success: bool = True
    message: str
    order_ref: str
    order_status: str
    payment_status: str
    total_price: Optional[float] = None
