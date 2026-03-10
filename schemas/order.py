from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class OrderItemIn(BaseModel):
    product_variant_id: int
    quantity: int = Field(..., ge=1)


class OrderIn(BaseModel):
    items: List[OrderItemIn] = Field(..., min_length=1, max_length=50)
    customer_name: str = Field(..., min_length=1, max_length=150)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    payment_method: str = Field(..., pattern="^(paynow)$")
    delivery_address: Optional[str] = None


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_variant_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_ref: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    subtotal: Decimal
    delivery_fee: Decimal
    total_price: Decimal
    payment_method: Optional[str] = None
    payment_status: str
    order_status: str
    payment_intent_id: Optional[str] = None
    delivery_address: Optional[str] = None
    created_at: datetime
    order_items: List[OrderItemOut] = []


class PaymentConfirmIn(BaseModel):
    payment_intent_id: str
