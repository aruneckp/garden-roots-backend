import logging

from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from typing import List

from database.models import StockInventory
from schemas.stock import StockResponse

logger = logging.getLogger(__name__)


def _build_stock_response(stock: StockInventory) -> StockResponse:
    net = stock.quantity_available - stock.reserved_quantity
    return StockResponse(
        product_variant_id=stock.product_variant_id,
        quantity_available=stock.quantity_available,
        reserved_quantity=stock.reserved_quantity,
        available_net=net,
        warehouse_location=stock.warehouse_location,
        last_updated=stock.last_updated,
        in_stock=net > 0,
    )


def get_stock(db: Session, product_variant_id: int) -> StockResponse:
    stock = (
        db.query(StockInventory)
        .filter(StockInventory.product_variant_id == product_variant_id)
        .first()
    )
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock for variant {product_variant_id} not found")
    return _build_stock_response(stock)


def check_bulk_stock(db: Session, variant_ids: List[int]) -> List[StockResponse]:
    stocks = (
        db.query(StockInventory)
        .filter(StockInventory.product_variant_id.in_(variant_ids))
        .all()
    )
    found_ids = {s.product_variant_id for s in stocks}
    missing = [vid for vid in variant_ids if vid not in found_ids]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"No stock record for variant(s): {missing}",
        )
    return [_build_stock_response(s) for s in stocks]


def reserve_stock(db: Session, product_variant_id: int, quantity: int):
    """
    Reserve stock atomically using a conditional UPDATE.
    ORA-02014 prevents SELECT ... FOR UPDATE with FETCH FIRST (LIMIT),
    so we use a direct UPDATE that only succeeds when stock is sufficient.
    """
    rows_updated = db.execute(
        text("""
            UPDATE stock_inventory
               SET reserved_quantity = reserved_quantity + :qty
             WHERE product_variant_id = :vid
               AND (quantity_available - reserved_quantity) >= :qty
        """),
        {"qty": quantity, "vid": product_variant_id},
    ).rowcount

    if rows_updated == 0:
        # Either the variant doesn't exist or insufficient stock — check which
        stock = (
            db.query(StockInventory)
            .filter(StockInventory.product_variant_id == product_variant_id)
            .first()
        )
        if not stock:
            raise HTTPException(status_code=404, detail=f"Stock record not found for variant {product_variant_id}")
        available = stock.quantity_available - stock.reserved_quantity
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient stock for variant {product_variant_id}. Available: {available}, Requested: {quantity}",
        )


def deduct_stock(db: Session, product_variant_id: int, quantity: int):
    """
    Permanently deduct stock after payment is confirmed.
    Logs an error if no row is matched — indicates a data integrity issue
    (stock record missing for a variant that was already reserved).
    """
    result = db.execute(
        text("""
            UPDATE stock_inventory
               SET quantity_available = GREATEST(0, quantity_available - :qty),
                   reserved_quantity  = GREATEST(0, reserved_quantity - :qty)
             WHERE product_variant_id = :vid
        """),
        {"qty": quantity, "vid": product_variant_id},
    )
    if result.rowcount == 0:
        logger.error(
            "deduct_stock: no stock row found for variant %d (qty=%d) — possible data integrity issue",
            product_variant_id, quantity,
        )


def release_stock(db: Session, product_variant_id: int, quantity: int):
    """Release reserved stock when order is cancelled."""
    result = db.execute(
        text("""
            UPDATE stock_inventory
               SET reserved_quantity = GREATEST(0, reserved_quantity - :qty)
             WHERE product_variant_id = :vid
        """),
        {"qty": quantity, "vid": product_variant_id},
    )
    if result.rowcount == 0:
        logger.warning(
            "release_stock: no stock row found for variant %d (qty=%d)",
            product_variant_id, quantity,
        )
