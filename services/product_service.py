from sqlalchemy.orm import Session, selectinload
from datetime import date
from typing import List, Optional
from fastapi import HTTPException

from database.models import Product, ProductVariant, StockInventory
from schemas.product import ProductOut, VariantOut, StockOut


def _current_price(variant: ProductVariant):
    """Return the currently active (price, currency) for a variant."""
    today = date.today()
    for p in variant.pricing:
        from_ok = (p.valid_from is None) or (p.valid_from <= today)
        to_ok   = (p.valid_to is None)   or (p.valid_to >= today)
        if from_ok and to_ok:
            return float(p.base_price), p.currency
    return None, "USD"


def _build_stock_out(stock: Optional[StockInventory]) -> Optional[StockOut]:
    if not stock:
        return None
    net = stock.quantity_available - stock.reserved_quantity
    return StockOut(
        quantity_available=stock.quantity_available,
        reserved_quantity=stock.reserved_quantity,
        available_net=net,
        warehouse_location=stock.warehouse_location,
    )


def _build_variant_out(variant: ProductVariant) -> VariantOut:
    price, currency = _current_price(variant)
    return VariantOut(
        id=variant.id,
        size_name=variant.size_name,
        unit=variant.unit,
        price=price,
        currency=currency,
        stock=_build_stock_out(variant.stock),
    )


def _build_product_out(product: Product) -> ProductOut:
    return ProductOut(
        id=product.id,
        name=product.name,
        description=product.description,
        origin=product.origin,
        season_start=product.season_start,
        season_end=product.season_end,
        tag=product.tag,
        is_active=product.is_active if product.is_active is not None else 1,
        variants=[_build_variant_out(v) for v in product.variants],
    )


def _eager_load_options():
    """Eager-load variants → pricing and variants → stock in two round-trips.
    Eliminates the N+1 problem: previously SQLAlchemy fired one query per
    product per relationship (pricing, stock), totalling 1 + N*2 queries.
    With selectinload this is always exactly 3 queries regardless of catalog size.
    """
    return [
        selectinload(Product.variants).selectinload(ProductVariant.pricing),
        selectinload(Product.variants).selectinload(ProductVariant.stock),
    ]


def get_all_products(db: Session) -> List[ProductOut]:
    products = (
        db.query(Product)
        .options(*_eager_load_options())
        .order_by(Product.id)
        .all()
    )
    return [_build_product_out(p) for p in products]


def get_product_by_id(db: Session, product_id: int) -> ProductOut:
    product = (
        db.query(Product)
        .options(*_eager_load_options())
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return _build_product_out(product)


def get_product_variants(db: Session, product_id: int) -> List[VariantOut]:
    product = (
        db.query(Product)
        .options(*_eager_load_options())
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return [_build_variant_out(v) for v in product.variants]
