import random
import string
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from config.settings import settings
from database.models import Order, OrderItem, Pricing, ProductVariant, User, Shipment
from schemas.order import OrderIn, OrderOut
from services.stock_service import reserve_stock, deduct_stock, release_stock


def _generate_order_ref() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"GR-{suffix}"


def _get_current_price(variant: ProductVariant) -> Decimal:
    today = date.today()
    for p in variant.pricing:
        from_ok = (p.valid_from is None) or (p.valid_from <= today)
        to_ok = (p.valid_to is None) or (p.valid_to >= today)
        if from_ok and to_ok:
            return Decimal(str(p.base_price))
    raise HTTPException(
        status_code=422,
        detail=f"No active price found for variant {variant.id} ({variant.size_name})",
    )


def create_order(db: Session, payload: OrderIn, booked_by_admin=None) -> OrderOut:
    # 1. Resolve variants and prices
    line_items = []
    subtotal = Decimal("0")

    for item in payload.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.product_variant_id).first()
        if not variant:
            raise HTTPException(status_code=404, detail=f"Product variant {item.product_variant_id} not found")

        price = _get_current_price(variant)
        item_subtotal = price * item.quantity
        subtotal += item_subtotal
        line_items.append((variant, item.quantity, price, item_subtotal))

    # 2. Compute delivery fee (always $0 for self-pickup)
    if payload.delivery_type == "pickup":
        delivery_fee = Decimal("0")
    else:
        threshold = Decimal(str(settings.delivery_free_threshold))
        delivery_fee = Decimal("0") if subtotal >= threshold else Decimal(str(settings.delivery_cost))
    total = subtotal + delivery_fee

    # 3. Reserve stock atomically
    for variant, qty, _, _ in line_items:
        reserve_stock(db, variant.id, qty)

    # 4. Persist order
    # Validate user_id — guard against stale client-side IDs after a DB migration
    resolved_user_id = None
    if payload.user_id is not None:
        exists = db.query(User.id).filter(User.id == payload.user_id).first()
        resolved_user_id = payload.user_id if exists else None

    # Auto-tag the latest active (non-completed) shipment
    latest_shipment = (
        db.query(Shipment)
        .filter(Shipment.status != "completed")
        .order_by(Shipment.created_at.desc())
        .first()
    )

    is_pay_later = payload.payment_method == "pay_later"

    order = Order(
        order_ref=_generate_order_ref(),
        user_id=resolved_user_id,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_phone=payload.customer_phone,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total_price=total,
        payment_method=payload.payment_method,
        # pay_later orders are immediately confirmed; payment collected later by admin
        payment_status="pending",
        order_status="confirmed" if is_pay_later else "pending",
        delivery_type=payload.delivery_type,
        delivery_address=payload.delivery_address,
        pickup_location_id=payload.pickup_location_id,
        customer_notes=payload.customer_notes,
        shipment_id=latest_shipment.id if latest_shipment else None,
        booked_by_admin_id=booked_by_admin.id if booked_by_admin else None,
        booked_by_admin_name=(
            getattr(booked_by_admin, 'full_name', None) or getattr(booked_by_admin, 'username', None)
        ) if booked_by_admin else None,
    )
    db.add(order)
    db.flush()

    for variant, qty, price, item_sub in line_items:
        db.add(OrderItem(
            order_id=order.id,
            product_variant_id=variant.id,
            quantity=qty,
            unit_price=price,
            subtotal=item_sub,
        ))

    # pay_later: deduct stock immediately (admin confirmed the order; payment collected later)
    if is_pay_later:
        for variant, qty, _, _ in line_items:
            deduct_stock(db, variant.id, qty)

    db.commit()
    db.refresh(order)
    return _to_out(order)


def get_order(db: Session, order_id: int) -> OrderOut:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return _to_out(order)


def get_order_status(db: Session, order_id: int) -> dict:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return {
        "order_id":       order.id,
        "order_ref":      order.order_ref,
        "payment_status": order.payment_status,
        "order_status":   order.order_status,
    }


def confirm_payment(db: Session, order_id: int, payment_intent_id: str) -> OrderOut:
    # Oracle ORA-02014 forbids SELECT ... FETCH FIRST n ROWS ONLY FOR UPDATE,
    # so we cannot use .with_for_update().first().
    # Instead, use an atomic conditional UPDATE (same pattern as reserve_stock):
    #   - Only updates rows where payment_status IS STILL 'pending'
    #   - rowcount=0 means either not found or already confirmed — disambiguate below
    # This is race-safe: two concurrent calls both issue the UPDATE; exactly one
    # will see rowcount=1, the other sees rowcount=0 and gets a 409.
    rows_updated = db.execute(
        text("""
            UPDATE orders
               SET payment_status    = 'succeeded',
                   order_status      = 'confirmed',
                   payment_intent_id = :pi_id
             WHERE id             = :order_id
               AND payment_status = 'pending'
        """),
        {"pi_id": payment_intent_id, "order_id": order_id},
    ).rowcount

    if rows_updated == 0:
        # Disambiguate: does the order exist at all, or was it already confirmed?
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        raise HTTPException(status_code=409, detail="Payment already confirmed")

    # Fetch the freshly updated order to deduct stock and return it
    order = db.query(Order).filter(Order.id == order_id).first()
    for item in order.order_items:
        deduct_stock(db, item.product_variant_id, item.quantity)

    db.commit()
    db.refresh(order)
    return _to_out(order)


def cancel_order(db: Session, order_id: int) -> dict:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    if order.order_status in ("shipped", "delivered"):
        raise HTTPException(status_code=409, detail="Cannot cancel an order that is already shipped or delivered")
    # Stock has already been permanently deducted after payment — releasing it
    # would create phantom inventory. Paid orders need a proper refund flow instead.
    if order.payment_status == "succeeded":
        raise HTTPException(
            status_code=409,
            detail="Cannot cancel a paid order. Please contact support for a refund.",
        )

    for item in order.order_items:
        release_stock(db, item.product_variant_id, item.quantity)

    order.payment_status = "cancelled"
    order.order_status   = "cancelled"
    db.commit()
    return {"order_ref": order.order_ref, "order_status": "cancelled"}


def _to_out(order: Order) -> OrderOut:
    return OrderOut.model_validate(order)
