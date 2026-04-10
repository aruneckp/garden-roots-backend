import re

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database.connection import get_db
from database.models import DeliveryBoy, Order, OrderItem
from utils.auth import verify_password, create_delivery_token, verify_token
from schemas.admin import DeliveryBoyLoginIn, DeliveryBoyTokenOut
from services.delivery_fee_service import get_delivery_fee_async

router = APIRouter(prefix="/delivery", tags=["delivery"])


# ─── Auth dependency ────────────────────────────────────────────────────────

def get_current_delivery_boy(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> DeliveryBoy:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    payload = verify_token(parts[1])
    if payload.get("role") != "delivery_boy":
        raise HTTPException(status_code=403, detail="Not a delivery boy token")
    boy = db.query(DeliveryBoy).filter(
        DeliveryBoy.id == payload.get("user_id"),
        DeliveryBoy.is_active == 1,
    ).first()
    if not boy:
        raise HTTPException(status_code=401, detail="Delivery boy not found or inactive")
    return boy


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/fee")
async def get_fee(postal_code: str):
    """
    Calculate delivery fee for a Singapore postal code using Google Distance Matrix.
    Returns fee (SGD), driving distance (km), and zone label.
    No authentication required — called from the checkout UI.
    """
    if not re.match(r"^\d{6}$", postal_code):
        raise HTTPException(status_code=422, detail="postal_code must be exactly 6 digits")
    return await get_delivery_fee_async(postal_code)


@router.post("/login", response_model=DeliveryBoyTokenOut)
def delivery_login(payload: DeliveryBoyLoginIn, db: Session = Depends(get_db)):
    """Delivery boy login."""
    boy = db.query(DeliveryBoy).filter(DeliveryBoy.username == payload.username).first()
    if not boy or not verify_password(payload.password, boy.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not boy.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    token = create_delivery_token(boy.id, boy.username)
    return DeliveryBoyTokenOut(
        access_token=token,
        delivery_boy_id=boy.id,
        username=boy.username,
        full_name=boy.full_name,
    )


@router.get("/my-orders")
def get_my_orders(
    boy: DeliveryBoy = Depends(get_current_delivery_boy),
    db: Session = Depends(get_db),
):
    """Return orders for this delivery boy's latest delivery code."""
    # Find the latest delivery_code for this delivery boy
    latest = (
        db.query(Order.delivery_code)
        .filter(Order.delivery_boy_id == boy.id, Order.delivery_code.isnot(None))
        .order_by(Order.assigned_at.desc())
        .first()
    )
    if not latest:
        return {"delivery_code": None, "orders": []}

    latest_code = latest[0]
    orders = (
        db.query(Order)
        .filter(Order.delivery_boy_id == boy.id, Order.delivery_code == latest_code)
        .order_by(Order.assigned_at.asc())
        .all()
    )

    result = []
    for o in orders:
        items = [
            {
                "product_variant_id": i.product_variant_id,
                "quantity": i.quantity,
                "subtotal": str(i.subtotal),
            }
            for i in o.order_items
        ]
        result.append({
            "id": o.id,
            "order_ref": o.order_ref,
            "customer_name": o.customer_name,
            "customer_phone": o.customer_phone,
            "delivery_address": o.delivery_address,
            "total_price": str(o.total_price),
            "order_status": o.order_status,
            "delivery_code": o.delivery_code,
            "assigned_at": o.assigned_at.isoformat() if o.assigned_at else None,
            "items": items,
        })

    return {"delivery_code": latest_code, "orders": result}


@router.put("/orders/{order_id}/delivered")
def mark_order_delivered(
    order_id: int,
    boy: DeliveryBoy = Depends(get_current_delivery_boy),
    db: Session = Depends(get_db),
):
    """Mark an assigned order as delivered."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.delivery_boy_id == boy.id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or not assigned to you")
    order.order_status = "delivered"
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "order_ref": order.order_ref, "order_status": "delivered"}
