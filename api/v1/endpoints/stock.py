from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from schemas.stock import StockResponse, StockCheckRequest
from schemas.common import APIResponse
from services import stock_service

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("/{product_variant_id}", response_model=APIResponse[StockResponse])
def get_stock(product_variant_id: int, db: Session = Depends(get_db)):
    """Get current stock level for a single product variant."""
    data = stock_service.get_stock(db, product_variant_id)
    return APIResponse(data=data)


@router.post("/check", response_model=APIResponse[List[StockResponse]])
def check_bulk_stock(payload: StockCheckRequest, db: Session = Depends(get_db)):
    """Batch check stock for multiple variants at once."""
    data = stock_service.check_bulk_stock(db, payload.variant_ids)
    return APIResponse(data=data)
