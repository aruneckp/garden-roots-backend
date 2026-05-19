import re

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional

from database.connection import get_db
from schemas.order import OrderIn, OrderOut, PaymentConfirmIn, BulkOrderIn, BulkOrderOut, BulkOrderRowResult
from schemas.common import APIResponse
from services import order_service
from utils.auth import get_optional_admin, get_current_admin, verify_token

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/address-lookup")
def address_lookup(
    phone: str = Query(..., min_length=6),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Return distinct delivery addresses for address auto-fill at checkout.
    - Admin token  → phone-based lookup across all orders.
    - User token   → returns only addresses from the user's own orders (by user_id).
    - No token     → empty (no data exposed to guests).
    """
    # --- Auth gate ---
    if not authorization:
        return APIResponse(data=[])

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return APIResponse(data=[])

    try:
        payload = verify_token(parts[1])
    except Exception:
        return APIResponse(data=[])

    role = payload.get("role", "")

    if role == "admin":
        # Admin: phone-based lookup across all orders
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 6:
            return APIResponse(data=[])
        suffix = digits[-8:]
        _sql = text("""
            SELECT delivery_address,
                   COUNT(id)        AS order_count,
                   MAX(created_at)  AS last_used
              FROM orders
             WHERE REGEXP_REPLACE(customer_phone, '[^0-9]', '') LIKE :sfx
               AND delivery_type   = 'delivery'
               AND delivery_address IS NOT NULL
               AND LENGTH(TRIM(delivery_address)) > 0
             GROUP BY delivery_address
             ORDER BY MAX(created_at) DESC
             FETCH FIRST 5 ROWS ONLY
        """)
        _fallback_sql = text("""
            SELECT delivery_address,
                   COUNT(id)        AS order_count,
                   MAX(created_at)  AS last_used
              FROM orders
             WHERE customer_phone LIKE :sfx
               AND delivery_type   = 'delivery'
               AND delivery_address IS NOT NULL
               AND LENGTH(TRIM(delivery_address)) > 0
             GROUP BY delivery_address
             ORDER BY MAX(created_at) DESC
             FETCH FIRST 5 ROWS ONLY
        """)
        params = {"sfx": f"%{suffix}"}
        try:
            rows = db.execute(_sql, params).fetchall()
        except Exception:
            db.rollback()
            rows = db.execute(_fallback_sql, params).fetchall()

    elif role in ("user", "customer"):
        # Regular user: query strictly by their own user_id — never by phone.
        # Phone-based lookup would let anyone set their phone to a victim's number
        # (via PUT /users/me/phone, which has no OTP check) and then harvest addresses.
        user_id = payload.get("user_id")
        if not user_id:
            return APIResponse(data=[])
        _sql = text("""
            SELECT delivery_address,
                   COUNT(id)        AS order_count,
                   MAX(created_at)  AS last_used
              FROM orders
             WHERE user_id         = :user_id
               AND delivery_type   = 'delivery'
               AND delivery_address IS NOT NULL
               AND LENGTH(TRIM(delivery_address)) > 0
             GROUP BY delivery_address
             ORDER BY MAX(created_at) DESC
             FETCH FIRST 5 ROWS ONLY
        """)
        rows = db.execute(_sql, {"user_id": user_id}).fetchall()

    else:
        return APIResponse(data=[])

    suggestions = []
    for row in rows:
        addr = row.delivery_address or ''
        postal_match = re.search(r'Singapore\s+(\d{6})', addr, re.IGNORECASE)
        postal_code = postal_match.group(1) if postal_match else ''

        parts = [p.strip() for p in addr.split(',')]
        parts_no_postal = [p for p in parts if not re.search(r'Singapore\s*\d{6}', p, re.IGNORECASE)]

        unit_no = ''
        street = ''
        if len(parts_no_postal) >= 2:
            unit_no = parts_no_postal[0]
            street = ', '.join(parts_no_postal[1:])
        elif len(parts_no_postal) == 1:
            street = parts_no_postal[0]

        suggestions.append({
            'delivery_address': addr,
            'postal_code': postal_code,
            'unit_no': unit_no,
            'street': street,
            'order_count': row.order_count,
            'last_used': row.last_used.isoformat() if row.last_used else None,
        })

    return APIResponse(data=suggestions)


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
