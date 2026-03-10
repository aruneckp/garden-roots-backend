from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_db
from schemas.order import OrderIn, OrderOut, PaymentConfirmIn
from schemas.common import APIResponse
from services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=APIResponse[OrderOut], status_code=201)
def create_order(payload: OrderIn, db: Session = Depends(get_db)):
    """
    Create a new order.
    Validates stock, reserves inventory, computes delivery fee, and persists to Oracle.
    """
    data = order_service.create_order(db, payload)
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
