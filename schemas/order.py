from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing import Optional, List, Literal
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
    payment_method: str = Field(..., pattern="^(paynow|pay_later)$")
    delivery_type: Literal["delivery", "pickup"] = "delivery"
    delivery_address: Optional[str] = None
    pickup_location_id: Optional[int] = None
    customer_notes: Optional[str] = Field(None, max_length=1000)
    postal_code: Optional[str] = Field(None, pattern=r"^\d{6}$")
    user_id: Optional[int] = None  # set when user is logged in
    promo_code: Optional[str] = Field(None, max_length=50)

    @model_validator(mode="after")
    def validate_delivery_requirements(self) -> "OrderIn":
        if self.delivery_type == "delivery" and not (self.delivery_address or "").strip():
            raise ValueError("delivery_address is required for home delivery orders")
        if self.delivery_type == "pickup" and not self.pickup_location_id:
            raise ValueError("pickup_location_id is required for self-pickup orders")
        return self


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_variant_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class PickupLocationPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    phone: Optional[str] = None
    whatsapp_phone: Optional[str] = None


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
    delivery_type: str = "delivery"
    delivery_address: Optional[str] = None
    pickup_location_id: Optional[int] = None
    pickup_location: Optional[PickupLocationPublicOut] = None
    shipment_id: Optional[int] = None
    customer_notes: Optional[str] = None
    promo_code: Optional[str] = None
    discount_amount: Decimal = Decimal("0")
    created_at: datetime
    order_items: List[OrderItemOut] = []


class PaymentConfirmIn(BaseModel):
    payment_intent_id: str
