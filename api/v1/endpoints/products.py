from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from pydantic import BaseModel
from datetime import date

from database.connection import get_db
from database.models import Product, ProductVariant, Pricing
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


class PriceUpdate(BaseModel):
    price: float


@router.patch("/{product_id}/price", response_model=APIResponse[ProductOut])
def update_product_price(
    product_id: int,
    body: PriceUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Update the base price for the currently active pricing row of a product."""
    variant = db.query(ProductVariant).filter(ProductVariant.product_id == product_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail=f"No variant found for product {product_id}")
    today = date.today()
    # Find the currently active pricing record (same logic as _current_price in product_service)
    pricing = (
        db.query(Pricing)
        .filter(
            Pricing.product_variant_id == variant.id,
            or_(Pricing.valid_from == None, Pricing.valid_from <= today),
            or_(Pricing.valid_to == None, Pricing.valid_to >= today),
        )
        .first()
    )
    # Fall back to any pricing row if none is currently active
    if not pricing:
        pricing = db.query(Pricing).filter(Pricing.product_variant_id == variant.id).first()
    if not pricing:
        raise HTTPException(status_code=404, detail=f"No pricing record found for variant {variant.id}")
    pricing.base_price = body.price
    db.commit()
    data = product_service.get_product_by_id(db, product_id)
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
