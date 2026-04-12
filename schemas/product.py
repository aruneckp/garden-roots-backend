from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import date


class PricingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    base_price: Decimal
    currency: str
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quantity_available: int
    reserved_quantity: int
    available_net: int
    warehouse_location: Optional[str] = None


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    size_name: str
    unit: str
    price: Optional[Decimal] = None
    currency: str = "USD"
    stock: Optional[StockOut] = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    origin: Optional[str] = None
    season_start: Optional[str] = None
    season_end: Optional[str] = None
    tag: Optional[str] = None
    is_active: int = 1
    variants: List[VariantOut] = []
