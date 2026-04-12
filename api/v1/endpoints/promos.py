from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_db
from schemas.common import APIResponse
from schemas.promo import (
    PromoValidateIn, PromoValidateOut,
    PromoCodeIn, PromoCodeOut, PromoCodeUpdate,
)
from services import promo_service
from utils.auth import get_current_admin, get_optional_admin

router = APIRouter(prefix="/promos", tags=["promos"])


# ── Public: validate a promo code ─────────────────────────────────────────────

@router.post("/validate", response_model=APIResponse[PromoValidateOut])
def validate_promo(
    payload: PromoValidateIn,
    db: Session = Depends(get_db),
    admin=Depends(get_optional_admin),
):
    """
    Validate a promo code against the current cart subtotal, user, and delivery context.
    Returns the discount amount if valid; raises 400 with a user-facing reason if not.
    When called with a valid admin token, user-specific and redemption-limit checks are skipped.
    """
    result = promo_service.validate_promo(
        db,
        code=payload.code,
        order_subtotal=payload.order_subtotal,
        user_id=payload.user_id,
        delivery_type=payload.delivery_type,
        pickup_location_id=payload.pickup_location_id,
        is_admin_override=admin is not None,
    )
    return APIResponse(data=result, message=result["message"])


# ── Admin CRUD ────────────────────────────────────────────────────────────────

@router.post("/admin", response_model=APIResponse[PromoCodeOut], status_code=201)
def create_promo(
    payload: PromoCodeIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Create a new promo code (admin only)."""
    data = promo_service.create_promo(db, payload)
    return APIResponse(data=data, message=f"Promo code '{data.code}' created")


@router.get("/admin", response_model=APIResponse[list[PromoCodeOut]])
def list_promos(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """List all promo codes (admin only)."""
    data = promo_service.list_promos(db)
    return APIResponse(data=data)


@router.put("/admin/{promo_id}", response_model=APIResponse[PromoCodeOut])
def update_promo(
    promo_id: int,
    payload: PromoCodeUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Update a promo code — expiry, discount value, redemption limit, or active status (admin only)."""
    data = promo_service.update_promo(db, promo_id, payload)
    return APIResponse(data=data, message="Promo code updated")
