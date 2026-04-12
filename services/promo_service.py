"""
Promo code validation and CRUD.

Validation rules:
  1. Code must exist and be active (is_active=1)
  2. Expiry: valid until 23:59:59 SST on expiry_date
  3. user_specific: only the designated user_id may use it
  4. location_specific: only valid when delivery_type=pickup and matching pickup_location_id
  5. min_order_amount: subtotal must meet the floor
  6. Per-user redemption_limit: user must not have used it too many times

Usage recording:
  - PromoUsage row is written inside create_order after db.flush() (order ID exists)
  - promo.total_used is incremented
  - user_specific promos are auto-deactivated when the user hits their limit
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database.models import PromoCode, PromoUsage, PickupLocation
from schemas.promo import PromoCodeIn, PromoCodeUpdate

logger = logging.getLogger(__name__)

# Singapore Standard Time (UTC+8)
SST = timezone(timedelta(hours=8))


# ── Public validation (called from checkout + order creation) ─────────────────

def validate_promo(
    db: Session,
    code: str,
    order_subtotal: Decimal,
    user_id: Optional[int],
    delivery_type: str,
    pickup_location_id: Optional[int],
    is_admin_override: bool = False,
) -> dict:
    """
    Validate a promo code and return discount info.
    Raises HTTPException with a user-facing message on any failure.
    """
    promo = (
        db.query(PromoCode)
        .filter(PromoCode.code == code.upper().strip(), PromoCode.is_active == 1)
        .first()
    )
    if not promo:
        raise HTTPException(status_code=400, detail="Promo code is invalid or inactive")

    # 1. Expiry check — valid until 23:59:59.999 SST on expiry_date
    now_sst = datetime.now(SST)
    expiry_sst = promo.expiry_date.astimezone(SST)
    expiry_end = expiry_sst.replace(hour=23, minute=59, second=59, microsecond=999999)
    if now_sst > expiry_end:
        raise HTTPException(status_code=400, detail="Promo code has expired")

    # 2. User-specific restriction (skipped when admin places the order)
    if promo.promo_type == "user_specific" and not is_admin_override:
        if not user_id or promo.specific_user_id != user_id:
            raise HTTPException(status_code=400, detail="This promo code is not applicable for your account")

    # 3. Location-specific restriction
    if promo.promo_type == "location_specific":
        if delivery_type != "pickup" or promo.specific_location_id != pickup_location_id:
            loc_label = ""
            if promo.specific_location_id:
                loc = db.query(PickupLocation).filter(PickupLocation.id == promo.specific_location_id).first()
                if loc:
                    loc_label = f" ({loc.name})"
            raise HTTPException(
                status_code=400,
                detail=f"This promo code is only valid for self-pickup at a specific location{loc_label}",
            )

    # 4. Minimum order amount
    subtotal = Decimal(str(order_subtotal))
    min_amt = Decimal(str(promo.min_order_amount))
    if subtotal < min_amt:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum order of ${min_amt:.2f} is required to use this promo code",
        )

    # 5. Per-user redemption limit (skipped when admin places the order)
    if user_id is not None and not is_admin_override:
        used_count = (
            db.query(PromoUsage)
            .filter(PromoUsage.promo_code_id == promo.id, PromoUsage.user_id == user_id)
            .count()
        )
        if used_count >= promo.redemption_limit:
            raise HTTPException(
                status_code=400,
                detail="You have already used this promo code the maximum number of times",
            )

    # 6. Calculate discount amount
    disc_val = Decimal(str(promo.discount_value))
    if promo.discount_type == "percentage":
        discount_amount = (subtotal * disc_val / Decimal("100")).quantize(Decimal("0.01"))
    else:
        discount_amount = disc_val

    # Cap at subtotal (can never discount more than the order value)
    discount_amount = min(discount_amount, subtotal).quantize(Decimal("0.01"))

    return {
        "promo_code_id":  promo.id,
        "code":           promo.code,
        "discount_type":  promo.discount_type,
        "discount_value": disc_val,
        "discount_amount": discount_amount,
        "message": f"Promo code applied! You save ${discount_amount:.2f}",
    }


def record_promo_usage(db: Session, promo_code_id: int, user_id: Optional[int], order_id: int) -> None:
    """
    Write a PromoUsage row and increment total_used.
    Auto-deactivates user_specific promos when the user hits their limit.
    Called inside create_order after db.flush() (so order.id is set).
    Does NOT commit — the caller (order_service) owns the transaction.
    """
    promo = db.query(PromoCode).filter(PromoCode.id == promo_code_id).first()
    if not promo:
        logger.warning("record_promo_usage: promo_code_id %s not found", promo_code_id)
        return

    db.add(PromoUsage(promo_code_id=promo_code_id, user_id=user_id, order_id=order_id))
    promo.total_used = (promo.total_used or 0) + 1

    # Auto-expire user_specific promos when that user has exhausted their limit
    if promo.promo_type == "user_specific" and user_id is not None:
        used_count = (
            db.query(PromoUsage)
            .filter(PromoUsage.promo_code_id == promo_code_id, PromoUsage.user_id == user_id)
            .count()
        )
        # +1 for the row we just added (not yet flushed)
        if (used_count + 1) >= promo.redemption_limit:
            promo.is_active = 0
            logger.info("PromoCode %s auto-deactivated (user %s reached limit)", promo.code, user_id)


# ── Admin CRUD ────────────────────────────────────────────────────────────────

def create_promo(db: Session, payload: PromoCodeIn) -> PromoCode:
    code_upper = payload.code.upper().strip()
    existing = db.query(PromoCode).filter(PromoCode.code == code_upper).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Promo code '{code_upper}' already exists")

    promo = PromoCode(
        code=code_upper,
        promo_type=payload.promo_type,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        expiry_date=payload.expiry_date,
        min_order_amount=payload.min_order_amount,
        redemption_limit=payload.redemption_limit,
        specific_user_id=payload.specific_user_id,
        specific_location_id=payload.specific_location_id,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return promo


def list_promos(db: Session) -> list:
    return db.query(PromoCode).order_by(PromoCode.created_at.desc()).all()


def get_promo(db: Session, promo_id: int) -> PromoCode:
    promo = db.query(PromoCode).filter(PromoCode.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail=f"Promo code {promo_id} not found")
    return promo


def update_promo(db: Session, promo_id: int, payload: PromoCodeUpdate) -> PromoCode:
    promo = get_promo(db, promo_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(promo, field, value)
    db.commit()
    db.refresh(promo)
    return promo
