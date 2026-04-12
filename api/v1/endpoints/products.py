from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from database.models import Product
from schemas.product import ProductOut, VariantOut
from schemas.common import APIResponse
from services import product_service
from utils.auth import get_current_admin

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


@router.patch("/{product_id}/active", response_model=APIResponse[ProductOut])
def toggle_product_active(
    product_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Enable or disable a product. Requires admin authentication."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    current = product.is_active if product.is_active is not None else 1
    product.is_active = 0 if current else 1
    db.commit()
    db.refresh(product)
    data = product_service.get_product_by_id(db, product_id)
    return APIResponse(data=data)
