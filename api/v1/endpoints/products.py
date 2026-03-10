from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from schemas.product import ProductOut, VariantOut
from schemas.common import APIResponse
from services import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=APIResponse[List[ProductOut]])
def list_products(db: Session = Depends(get_db)):
    """Return all products with variants, current pricing, and stock levels."""
    data = product_service.get_all_products(db)
    return APIResponse(data=data)


@router.get("/{product_id}", response_model=APIResponse[ProductOut])
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Return a single product by ID."""
    data = product_service.get_product_by_id(db, product_id)
    return APIResponse(data=data)


@router.get("/{product_id}/variants", response_model=APIResponse[List[VariantOut]])
def get_variants(product_id: int, db: Session = Depends(get_db)):
    """Return all variants for a product."""
    data = product_service.get_product_variants(db, product_id)
    return APIResponse(data=data)
