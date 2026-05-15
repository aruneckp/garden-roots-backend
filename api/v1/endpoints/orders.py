from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from schemas.order import OrderIn, OrderOut, PaymentConfirmIn, BulkOrderIn, BulkOrderOut, BulkOrderRowResult
from schemas.common import APIResponse
from services import order_service
from utils.auth import get_optional_admin, get_current_admin

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=APIResponse[OrderOut], status_code=201)
async def create_order(
    payload: OrderIn,
    db: Session = Depends(get_db),
    booked_by_admin=Depends(get_optional_admin),
):
    """
    Create a new order.
    Validates stock, reserves inventory, computes delivery fee, and persists to Oracle.
    If an admin token is present, records which admin booked the order.
    """
    data = order_service.create_order(db, payload, booked_by_admin=booked_by_admin)
    return APIResponse(data=data, message="Order created successfully")


@router.get("/{order_id}", response_model=APIResponse[OrderOut])
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get full order details by ID."""
    data = order_service.get_order(db, order_id)
    return APIResponse(data=data)


@router.get("/{order_id}/status", response_model=APIResponse[dict])
def get_order_status(order_id: int, db: Session = Depends(get_db)):
    """Get lightweight order status (payment_status + order_status)."""
    data = order_service.get_order_status(db, order_id)
    return APIResponse(data=data)


@router.put("/{order_id}/payment-confirm", response_model=APIResponse[OrderOut])
def confirm_payment(order_id: int, payload: PaymentConfirmIn, db: Session = Depends(get_db)):
    """
    Confirm payment for an order.
    Updates payment_status to 'succeeded', deducts stock permanently.
    """
    data = order_service.confirm_payment(db, order_id, payload.payment_intent_id)
    return APIResponse(data=data, message="Payment confirmed")


@router.delete("/{order_id}/cancel", response_model=APIResponse[dict])
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    """Cancel an order and release reserved stock."""
    data = order_service.cancel_order(db, order_id)
    return APIResponse(data=data, message="Order cancelled")


@router.post("/bulk", response_model=APIResponse[BulkOrderOut])
async def create_orders_bulk(
    payload: BulkOrderIn,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Bulk-create multiple orders in one request. Admin only.
    Each row is processed independently — failures don't block other rows.
    Returns per-row success/error detail plus a summary count.
    """
    results: List[BulkOrderRowResult] = []
    for i, order_in in enumerate(payload.orders):
        try:
            order = order_service.create_order(db, order_in, booked_by_admin=admin)
            results.append(BulkOrderRowResult(
                row=i + 1,
                success=True,
                order_ref=order.order_ref,
                order_id=order.id,
                customer_name=order.customer_name,
            ))
        except Exception as exc:
            results.append(BulkOrderRowResult(
                row=i + 1,
                success=False,
                customer_name=order_in.customer_name,
                error=str(exc),
            ))

    succeeded = sum(1 for r in results if r.success)
    return APIResponse(
        data=BulkOrderOut(
            total=len(results),
            succeeded=succeeded,
            failed=len(results) - succeeded,
            results=results,
        ),
        message=f"Processed {len(results)} orders: {succeeded} succeeded, {len(results) - succeeded} failed",
    )
