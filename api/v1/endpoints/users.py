"""
Customer user endpoints — all require a valid user JWT.
"""
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from database.connection import get_db
from database.models import User, Order
from schemas.order import PickupLocationPublicOut
from utils.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UserProfileOut(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class PhoneUpdateIn(BaseModel):
    phone: str


class FeedbackIn(BaseModel):
    delivery_feedback: str = Field(..., min_length=1, max_length=2000)


class OrderItemSummary(BaseModel):
    product_variant_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True


class UserOrderOut(BaseModel):
    id: int
    order_ref: str
    customer_name: str
    subtotal: Decimal
    delivery_fee: Decimal
    total_price: Decimal
    payment_status: str
    order_status: str
    # Fulfilment details
    delivery_type: str = "delivery"
    delivery_address: Optional[str] = None
    pickup_location: Optional[PickupLocationPublicOut] = None
    shipment_id: Optional[int] = None
    # Notes & feedback
    customer_notes: Optional[str] = None
    delivery_feedback: Optional[str] = None
    created_at: datetime
    order_items: List[OrderItemSummary] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserProfileOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently logged-in user's profile."""
    return current_user


@router.put("/me/phone", response_model=UserProfileOut)
def update_phone(
    payload: PhoneUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save/update the user's phone number."""
    current_user.phone = payload.phone.strip()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/orders", response_model=List[UserOrderOut])
def get_my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all orders placed by the currently logged-in user, newest first."""
    orders = (
        db.query(Order)
        .options(
            selectinload(Order.order_items),
            selectinload(Order.pickup_location),
        )
        .filter(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return orders


@router.put("/me/orders/{order_id}/feedback", response_model=UserOrderOut)
def submit_feedback(
    order_id: int,
    payload: FeedbackIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Customer submits or updates delivery feedback on one of their orders.
    Allowed for any paid order (payment_status = 'succeeded').
    """
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.user_id == current_user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.payment_status != "succeeded":
        raise HTTPException(
            status_code=409,
            detail="Feedback can only be submitted for paid orders",
        )

    order.delivery_feedback = payload.delivery_feedback.strip()
    db.commit()
    db.refresh(order)
    return order
