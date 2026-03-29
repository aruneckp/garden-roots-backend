from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import AdminUser
from utils.auth import get_current_admin, verify_password, create_access_token, hash_password
from schemas.admin import (
    AdminLoginIn, AdminTokenOut,
    SPOCContactIn, SPOCContactOut,
    ShipmentIn, ShipmentOut, ShipmentDetailOut, ShipmentUpdate,
    ShipmentBoxIn, ShipmentBoxOut, ShipmentBoxUpdate,
    DeliveryLogIn, DeliveryLogOut,
    ShipmentConsolidatedSummary,
    PickupLocationIn, PickupLocationOut, PickupLocationUpdate, PickupLocationOccupancy,
    PrebookingIn, PrebookingOut, PrebookingStatusUpdate,
    PaymentRecordIn, PaymentRecordOut, PaymentRecordUpdate, PaymentSummary,
    BoxEntryLogOut,
    ShipmentBoxEnhancedOut, ShipmentBoxEntryIn,
)
from services.admin_service import (
    create_spoc_contact, get_spoc_contact, get_all_spoc_contacts,
    create_shipment, get_shipment, get_shipment_by_ref, get_all_shipments, update_shipment,
    add_box_to_shipment, get_shipment_box, update_shipment_box,
    log_delivery, get_delivery_logs,
    generate_shipment_summary, get_shipment_summary, get_dashboard_summary,
    # New functions
    create_pickup_location, get_all_pickup_locations, get_pickup_location, update_pickup_location, get_location_occupancy,
    create_prebooking, get_prebookings_for_shipment, update_prebooking_status,
    record_payment, get_payment_summary, mark_payment_paid,
    receive_shipment, add_box_entry, update_box_delivery_status, get_reception_status,
    get_shipment_status_report, get_pending_payments_across_shipments,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post("/login", response_model=AdminTokenOut)
def login(payload: AdminLoginIn, db: Session = Depends(get_db)):
    """Admin login endpoint."""
    user = db.query(AdminUser).filter(AdminUser.username == payload.username).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Admin account is inactive")

    token = create_access_token(user.id, user.username, user.role)

    return AdminTokenOut(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.post("/register", response_model=SPOCContactOut)
def register_admin(payload: AdminLoginIn, db: Session = Depends(get_db)):
    """Register a new admin user (should be protected in production)."""
    # Check if username already exists
    existing_user = db.query(AdminUser).filter(AdminUser.username == payload.username).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Username already exists")

    # Create new admin user
    user = AdminUser(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="admin",
        is_active=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return SPOCContactOut(
        id=user.id,
        name=payload.username,
        phone="",
        email=None,
        location=None,
        created_at=user.created_at,
    )


# ============================================================================
# SPOC Contact Endpoints
# ============================================================================

@router.post("/spoc-contacts", response_model=SPOCContactOut)
def create_spoc(
    payload: SPOCContactIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new SPOC contact."""
    return create_spoc_contact(db, payload)


@router.get("/spoc-contacts/{contact_id}", response_model=SPOCContactOut)
def get_spoc(
    contact_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get SPOC contact by ID."""
    return get_spoc_contact(db, contact_id)


@router.get("/spoc-contacts", response_model=list[SPOCContactOut])
def list_spoc_contacts(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all SPOC contacts."""
    return get_all_spoc_contacts(db)


# ============================================================================
# Shipment Endpoints
# ============================================================================

@router.post("/shipments", response_model=ShipmentOut)
def create_new_shipment(
    payload: ShipmentIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new shipment."""
    return create_shipment(db, payload)


@router.get("/shipments/{shipment_id}", response_model=ShipmentDetailOut)
def get_shipment_details(
    shipment_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get shipment details by ID."""
    return get_shipment(db, shipment_id)


@router.get("/shipments/ref/{shipment_ref}", response_model=ShipmentDetailOut)
def get_shipment_by_reference(
    shipment_ref: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get shipment details by reference."""
    return get_shipment_by_ref(db, shipment_ref)


@router.get("/shipments", response_model=list[ShipmentOut])
def list_shipments(
    status: str = None,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all shipments, optionally filtered by status."""
    return get_all_shipments(db, status)


@router.put("/shipments/{shipment_id}", response_model=ShipmentDetailOut)
def update_shipment_details(
    shipment_id: int,
    payload: ShipmentUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update shipment details."""
    return update_shipment(db, shipment_id, payload)


# ============================================================================
# Shipment Box Endpoints
# ============================================================================

@router.post("/shipments/{shipment_id}/boxes", response_model=ShipmentBoxOut)
def add_box(
    shipment_id: int,
    payload: ShipmentBoxIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Add a box to a shipment."""
    return add_box_to_shipment(db, shipment_id, payload)


@router.get("/boxes/{box_id}", response_model=ShipmentBoxOut)
def get_box(
    box_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get box details."""
    return get_shipment_box(db, box_id)


@router.put("/boxes/{box_id}", response_model=ShipmentBoxOut)
def update_box(
    box_id: int,
    payload: ShipmentBoxUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update box status and delivery details."""
    return update_shipment_box(db, box_id, payload)


# ============================================================================
# Delivery Log Endpoints
# ============================================================================

@router.post("/boxes/{box_id}/delivery", response_model=DeliveryLogOut)
def log_box_delivery(
    box_id: int,
    payload: DeliveryLogIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Log delivery of a box."""
    return log_delivery(db, box_id, payload)


@router.get("/shipments/{shipment_id}/delivery-logs", response_model=list[DeliveryLogOut])
def list_delivery_logs(
    shipment_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all delivery logs for a shipment."""
    return get_delivery_logs(db, shipment_id)


# ============================================================================
# Summary & Reporting Endpoints
# ============================================================================

@router.get("/shipments/{shipment_id}/summary", response_model=ShipmentConsolidatedSummary)
def get_shipment_consolidated_summary(
    shipment_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get consolidated summary for a shipment."""
    return get_shipment_summary(db, shipment_id)


@router.post("/shipments/{shipment_id}/generate-summary", response_model=ShipmentConsolidatedSummary)
def generate_summary(
    shipment_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Generate/refresh consolidated summary for a shipment."""
    return generate_shipment_summary(db, shipment_id)


@router.get("/dashboard/summary")
def get_dashboard(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get overall dashboard summary across all shipments."""
    return get_dashboard_summary(db)


# ============================================================================
# Shipment Reception Endpoints
# ============================================================================

@router.post("/shipments/{shipment_id}/receive")
def receive_shipment_endpoint(
    shipment_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Mark shipment as physically received."""
    return receive_shipment(db, shipment_id)


@router.get("/shipments/{shipment_id}/reception-status")
def get_reception_status_endpoint(
    shipment_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get shipment reception progress."""
    return get_reception_status(db, shipment_id)


# ============================================================================
# Pickup Location Endpoints
# ============================================================================

@router.post("/pickup-locations", response_model=PickupLocationOut)
def create_location(
    payload: PickupLocationIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new pickup location."""
    return create_pickup_location(db, payload)


@router.get("/pickup-locations", response_model=list[PickupLocationOut])
def list_pickup_locations(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all active pickup locations."""
    return get_all_pickup_locations(db)


@router.get("/pickup-locations/{location_id}", response_model=PickupLocationOut)
def get_location(
    location_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get pickup location by ID."""
    return get_pickup_location(db, location_id)


@router.put("/pickup-locations/{location_id}", response_model=PickupLocationOut)
def update_location(
    location_id: int,
    payload: PickupLocationUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update pickup location."""
    return update_pickup_location(db, location_id, payload)


@router.get("/pickup-locations/{location_id}/occupancy", response_model=PickupLocationOccupancy)
def get_location_occupancy_endpoint(
    location_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get location occupancy information."""
    return get_location_occupancy(db, location_id)


# ============================================================================
# Prebooking Endpoints
# ============================================================================

@router.post("/prebookings", response_model=PrebookingOut)
def create_prebooking_endpoint(
    payload: PrebookingIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new prebooking for a box."""
    return create_prebooking(db, payload)


@router.get("/shipments/{shipment_id}/prebookings", response_model=list[PrebookingOut])
def list_prebookings(
    shipment_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all prebookings for a shipment."""
    return get_prebookings_for_shipment(db, shipment_id)


@router.put("/prebookings/{prebooking_id}/status", response_model=PrebookingOut)
def update_prebooking_status_endpoint(
    prebooking_id: int,
    payload: PrebookingStatusUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update prebooking status."""
    return update_prebooking_status(db, prebooking_id, payload)


# ============================================================================
# Payment Endpoints
# ============================================================================

@router.post("/payments", response_model=PaymentRecordOut)
def record_payment_endpoint(
    payload: PaymentRecordIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Record a payment for a box."""
    return record_payment(db, payload)


@router.get("/shipments/{shipment_id}/payments", response_model=PaymentSummary)
def get_shipment_payments(
    shipment_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get payment summary for a shipment."""
    return get_payment_summary(db, shipment_id)


@router.put("/payments/{payment_id}/mark-paid", response_model=PaymentRecordOut)
def mark_payment_as_paid(
    payment_id: int,
    payload: PaymentRecordUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Mark a payment as paid."""
    return mark_payment_paid(db, payment_id, payload)


@router.get("/payments/pending", response_model=dict)
def get_pending_payments(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all pending payments across shipments."""
    return get_pending_payments_across_shipments(db)


# ============================================================================
# Box Entry and Management Endpoints
# ============================================================================

@router.post("/boxes/{box_id}/entry", response_model=ShipmentBoxEnhancedOut)
def enter_box_details(
    box_id: int,
    payload: ShipmentBoxEntryIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Record box entry with receiver, location, type, and payment info."""
    return add_box_entry(db, box_id, payload)


@router.put("/boxes/{box_id}/delivery-status", response_model=ShipmentBoxEnhancedOut)
def update_box_status(
    box_id: int,
    delivery_status: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update box delivery status."""
    return update_box_delivery_status(db, box_id, delivery_status)


@router.get("/shipments/{shipment_id}/boxes", response_model=list[ShipmentBoxEnhancedOut])
def get_shipment_boxes(
    shipment_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all boxes for a shipment with their status and payment info."""
    from database.models import ShipmentBox
    boxes = db.query(ShipmentBox).filter(ShipmentBox.shipment_id == shipment_id).all()
    return boxes


# ============================================================================
# Reporting Endpoints
# ============================================================================

@router.get("/shipments/{shipment_id}/status-report", response_model=dict)
def get_shipment_status_report_endpoint(
    shipment_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed status report for a shipment."""
    return get_shipment_status_report(db, shipment_id)

