from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from decimal import Decimal
from datetime import datetime


class PromoValidateIn(BaseModel):
    code: str
    order_subtotal: Decimal
    user_id: Optional[int] = None
    delivery_type: str = "delivery"
    pickup_location_id: Optional[int] = None


class PromoValidateOut(BaseModel):
    promo_code_id: int
    code: str
    discount_type: str
    discount_value: Decimal
    discount_amount: Decimal
    message: str


class PromoCodeIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    promo_type: Literal["global", "user_specific", "location_specific"] = "global"
    discount_type: Literal["fixed", "percentage"] = "fixed"
    discount_value: Decimal = Field(..., gt=0)
    expiry_date: datetime
    min_order_amount: Decimal = Field(default=Decimal("0"), ge=0)
    redemption_limit: int = Field(default=1, ge=1)
    specific_user_id: Optional[int] = None
    specific_location_id: Optional[int] = None


class PromoCodeUpdate(BaseModel):
    expiry_date: Optional[datetime] = None
    min_order_amount: Optional[Decimal] = None
    redemption_limit: Optional[int] = None
    discount_value: Optional[Decimal] = None
    is_active: Optional[int] = None


class PromoCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    promo_type: str
    discount_type: str
    discount_value: Decimal
    expiry_date: datetime
    min_order_amount: Decimal
    redemption_limit: int
    total_used: int
    is_active: int
    specific_user_id: Optional[int] = None
    specific_location_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
