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
# Payment schemas (Stripe PayNow)
# ---------------------------------------------------------------------------

class PaymentCreateRequest(BaseModel):
    amount: float
    description: str = "Garden Roots Order"
    order_id: int
    payment_method: Optional[str] = "paynow"


class PaymentCreateResponse(BaseModel):
    payment_intent_id: str
    client_secret: Optional[str] = None
    qr_url: Optional[str] = None       # Stripe-hosted PNG QR image URL
    qr_data: Optional[str] = None      # Raw PayNow EMV string (for debugging)
    status: str
    amount: float
    currency: str = "SGD"
    expires_at: Optional[int] = None


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
