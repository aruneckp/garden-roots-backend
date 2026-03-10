from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


class StockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_variant_id: int
    quantity_available: int
    reserved_quantity: int
    available_net: int
    warehouse_location: Optional[str] = None
    last_updated: Optional[datetime] = None
    in_stock: bool


class StockCheckRequest(BaseModel):
    variant_ids: List[int] = Field(..., min_length=1)
