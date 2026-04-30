from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

from database.connection import get_db
from database.models import Product, ProductVariant, Pricing, StockInventory
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


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    origin: Optional[str] = None
    tag: Optional[str] = None
    season_start: Optional[str] = None
    season_end: Optional[str] = None
    image_url: Optional[str] = None
    emoji: Optional[str] = None
    size_name: str = "Standard"
    unit: str = "box"
    price: float
    currency: str = "SGD"
    initial_stock: int = 0


@router.post("", response_model=APIResponse[ProductOut], status_code=201)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Create a new product with one variant and an initial price."""
    existing = db.query(Product).filter(Product.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Product '{body.name}' already exists")

    product = Product(
        name=body.name,
        description=body.description,
        origin=body.origin,
        tag=body.tag,
        season_start=body.season_start,
        season_end=body.season_end,
        image_url=body.image_url,
        emoji=body.emoji,
        is_active=1,
    )
    db.add(product)
    db.flush()

    variant = ProductVariant(
        product_id=product.id,
        size_name=body.size_name,
        unit=body.unit,
    )
    db.add(variant)
    db.flush()

    pricing = Pricing(
        product_variant_id=variant.id,
        base_price=body.price,
        currency=body.currency,
    )
    db.add(pricing)

    stock = StockInventory(
        product_variant_id=variant.id,
        quantity_available=max(0, body.initial_stock),
        reserved_quantity=0,
    )
    db.add(stock)
    db.commit()

    data = product_service.get_product_by_id(db, product.id)
    return APIResponse(data=data)


class DisplayOrderItem(BaseModel):
    id: int
    display_order: int


@router.patch("/reorder", response_model=APIResponse[List[ProductOut]])
def reorder_products(
    body: List[DisplayOrderItem],
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Bulk-update display_order for all products. Accepts [{id, display_order}, ...]."""
    for item in body:
        product = db.query(Product).filter(Product.id == item.id).first()
        if product:
            product.display_order = item.display_order
    db.commit()
    data = product_service.get_all_products(db)
    return APIResponse(data=data)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    origin: Optional[str] = None
    tag: Optional[str] = None
    season_start: Optional[str] = None
    season_end: Optional[str] = None
    image_url: Optional[str] = None
    emoji: Optional[str] = None
    unit: Optional[str] = None
    price: Optional[float] = None


@router.patch("/{product_id}", response_model=APIResponse[ProductOut])
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Update editable fields of a product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    if body.name is not None:
        existing = db.query(Product).filter(Product.name == body.name, Product.id != product_id).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Product '{body.name}' already exists")
        product.name = body.name
    if body.description is not None:
        product.description = body.description
    if body.origin is not None:
        product.origin = body.origin
    if body.tag is not None:
        product.tag = body.tag
    if body.season_start is not None:
        product.season_start = body.season_start
    if body.season_end is not None:
        product.season_end = body.season_end
    if body.image_url is not None:
        product.image_url = body.image_url
    if body.emoji is not None:
        product.emoji = body.emoji
    db.commit()

    # Update variant unit and/or price if provided
    if body.unit is not None or body.price is not None:
        variant = db.query(ProductVariant).filter(ProductVariant.product_id == product_id).first()
        if variant:
            if body.unit is not None:
                variant.unit = body.unit
                db.commit()
            if body.price is not None:
                today = date.today()
                pricing = (
                    db.query(Pricing)
                    .filter(
                        Pricing.product_variant_id == variant.id,
                        or_(Pricing.valid_from == None, Pricing.valid_from <= today),
                        or_(Pricing.valid_to == None, Pricing.valid_to >= today),
                    )
                    .first()
                )
                if not pricing:
                    pricing = db.query(Pricing).filter(Pricing.product_variant_id == variant.id).first()
                if pricing:
                    pricing.base_price = body.price
                    db.commit()

    data = product_service.get_product_by_id(db, product_id)
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


class StockUpdate(BaseModel):
    quantity_available: int


@router.patch("/{product_id}/stock", response_model=APIResponse[ProductOut])
def update_product_stock(
    product_id: int,
    body: StockUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Set quantity_available for the first variant of a product."""
    if body.quantity_available < 0:
        raise HTTPException(status_code=422, detail="quantity_available must be >= 0")
    variant = db.query(ProductVariant).filter(ProductVariant.product_id == product_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail=f"No variant found for product {product_id}")
    stock = db.query(StockInventory).filter(StockInventory.product_variant_id == variant.id).first()
    if stock:
        stock.quantity_available = body.quantity_available
    else:
        db.add(StockInventory(product_variant_id=variant.id, quantity_available=body.quantity_available, reserved_quantity=0))
    db.commit()
    data = product_service.get_product_by_id(db, product_id)
    return APIResponse(data=data)


@router.delete("/{product_id}", response_model=APIResponse[dict])
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Permanently delete a product and all associated variants, pricing, and stock."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    variants = db.query(ProductVariant).filter(ProductVariant.product_id == product_id).all()
    for variant in variants:
        db.query(StockInventory).filter(StockInventory.product_variant_id == variant.id).delete()
        db.query(Pricing).filter(Pricing.product_variant_id == variant.id).delete()
    db.query(ProductVariant).filter(ProductVariant.product_id == product_id).delete()
    db.delete(product)
    db.commit()
    return APIResponse(data={"product_id": product_id, "deleted": True})


@router.post("/{product_id}/reset-stock", response_model=APIResponse[dict])
def reset_product_stock(
    product_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Reset stock to 0 for all variants of a single product.
    Creates a stock row if one is missing."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    variants = db.query(ProductVariant).filter(ProductVariant.product_id == product_id).all()
    for variant in variants:
        stock = db.query(StockInventory).filter(StockInventory.product_variant_id == variant.id).first()
        if stock:
            stock.quantity_available = 0
            stock.reserved_quantity = 0
        else:
            db.add(StockInventory(product_variant_id=variant.id, quantity_available=0, reserved_quantity=0))
    db.commit()
    return APIResponse(data={"product_id": product_id, "reset": len(variants)})
