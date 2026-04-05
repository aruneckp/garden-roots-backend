from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import AdminUser, DeliveryBoy, Order, OrderStatusLog
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
    DeliveryBoyIn, DeliveryBoyOut, AssignDeliveryIn,
    OrderBulkStatusIn, OrderShipmentUpdate, OrderBulkShipmentIn,
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
    get_shipment_order_stats,
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


@router.get("/shipments/{shipment_id}/order-stats", response_model=dict)
def get_order_stats(
    shipment_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get order status breakdown (booked, pending, in_transit, delivered, etc.) for a shipment."""
    return get_shipment_order_stats(db, shipment_id)


@router.get("/shipments/{shipment_id}/orders", response_model=list[dict])
def get_shipment_orders(
    shipment_id: int,
    order_status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    delivery_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all orders linked to a shipment with optional filters."""
    from datetime import datetime, timezone
    query = db.query(Order).filter(Order.shipment_id == shipment_id)
    if order_status:
        query = query.filter(Order.order_status == order_status)
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    if delivery_type:
        query = query.filter(Order.delivery_type == delivery_type)
    if date_from:
        try:
            query = query.filter(Order.created_at >= datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc))
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            query = query.filter(Order.created_at <= dt_to)
        except ValueError:
            pass
    orders = query.order_by(Order.created_at.desc()).all()
    result = []
    for o in orders:
        items = [
            {
                "variant": (
                    f"{i.product_variant.product.name} – {i.product_variant.size_name}"
                    if i.product_variant and i.product_variant.product else "—"
                ),
                "qty": i.quantity,
                "unit_price": str(i.unit_price),
                "subtotal": str(i.subtotal),
            }
            for i in o.order_items
        ]
        result.append({
            "id": o.id,
            "order_ref": o.order_ref,
            "customer_name": o.customer_name,
            "customer_email": o.customer_email,
            "customer_phone": o.customer_phone,
            "delivery_type": o.delivery_type,
            "delivery_address": o.delivery_address,
            "pickup_location_id": o.pickup_location_id,
            "pickup_location_name": o.pickup_location.name if o.pickup_location else None,
            "order_status": o.order_status,
            "payment_status": o.payment_status,
            "payment_method": o.payment_method,
            "subtotal": str(o.subtotal),
            "delivery_fee": str(o.delivery_fee),
            "total_price": str(o.total_price),
            "delivery_boy_id": o.delivery_boy_id,
            "delivery_boy_name": (o.delivery_boy.full_name or o.delivery_boy.username) if o.delivery_boy else None,
            "delivery_code": o.delivery_code,
            "assigned_at": o.assigned_at.isoformat() if o.assigned_at else None,
            "customer_notes": o.customer_notes,
            "shipment_id": o.shipment_id,
            "booked_by_admin_id": o.booked_by_admin_id,
            "booked_by_admin_name": o.booked_by_admin_name,
            "items": items,
            "items_count": len(items),
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
    return result


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


@router.get("/payments/pending", response_model=dict)
def get_pending_payments(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all pending payments across shipments."""
    return get_pending_payments_across_shipments(db)


@router.put("/payments/{payment_id}/mark-paid", response_model=PaymentRecordOut)
def mark_payment_as_paid(
    payment_id: int,
    payload: PaymentRecordUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Mark a payment as paid."""
    return mark_payment_paid(db, payment_id, payload)


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


# ============================================================================
# Delivery Boy Management Endpoints
# ============================================================================

@router.post("/delivery-boys", response_model=DeliveryBoyOut)
def create_delivery_boy(
    payload: DeliveryBoyIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new delivery boy account."""
    existing = db.query(DeliveryBoy).filter(DeliveryBoy.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    boy = DeliveryBoy(
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
    )
    db.add(boy)
    db.commit()
    db.refresh(boy)
    return boy


@router.get("/delivery-boys", response_model=list[DeliveryBoyOut])
def list_delivery_boys(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all delivery boys."""
    return db.query(DeliveryBoy).order_by(DeliveryBoy.full_name).all()


@router.get("/orders/unassigned", response_model=list[dict])
def get_unassigned_orders(
    shipment_id: Optional[int] = Query(None),
    order_status: Optional[str] = Query(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get paid home-delivery orders not yet assigned to a delivery boy."""
    query = (
        db.query(Order)
        .filter(
            Order.payment_status == "succeeded",
            Order.delivery_type == "delivery",
            Order.delivery_boy_id.is_(None),
        )
    )
    if shipment_id:
        query = query.filter(Order.shipment_id == shipment_id)
    if order_status:
        query = query.filter(Order.order_status == order_status)
    orders = query.order_by(Order.created_at.desc()).all()
    return [
        {
            "id": o.id,
            "order_ref": o.order_ref,
            "customer_name": o.customer_name,
            "customer_phone": o.customer_phone,
            "delivery_address": o.delivery_address,
            "total_price": str(o.total_price),
            "order_status": o.order_status,
            "shipment_id": o.shipment_id,
            "items_count": len(o.order_items),
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders
    ]


@router.get("/orders/assigned", response_model=list[dict])
def get_assigned_orders(
    delivery_boy_id: Optional[int] = Query(None),
    shipment_id: Optional[int] = Query(None),
    order_status: Optional[str] = Query(None),
    delivery_code: Optional[str] = Query(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get home-delivery orders that have been assigned to a delivery boy."""
    query = (
        db.query(Order)
        .filter(
            Order.delivery_type == "delivery",
            Order.delivery_boy_id.isnot(None),
        )
    )
    if delivery_boy_id:
        query = query.filter(Order.delivery_boy_id == delivery_boy_id)
    if shipment_id:
        query = query.filter(Order.shipment_id == shipment_id)
    if order_status:
        query = query.filter(Order.order_status == order_status)
    if delivery_code:
        query = query.filter(Order.delivery_code == delivery_code)
    orders = query.order_by(Order.assigned_at.desc()).all()
    return [
        {
            "id": o.id,
            "order_ref": o.order_ref,
            "customer_name": o.customer_name,
            "customer_phone": o.customer_phone,
            "delivery_address": o.delivery_address,
            "total_price": str(o.total_price),
            "order_status": o.order_status,
            "payment_status": o.payment_status,
            "shipment_id": o.shipment_id,
            "delivery_boy_id": o.delivery_boy_id,
            "delivery_boy_name": o.delivery_boy.full_name or o.delivery_boy.username if o.delivery_boy else None,
            "delivery_code": o.delivery_code,
            "assigned_at": o.assigned_at.isoformat() if o.assigned_at else None,
            "items_count": len(o.order_items),
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders
    ]


# ============================================================================
# Orders Management Endpoints
# ============================================================================

@router.get("/orders", response_model=list[dict])
def list_all_orders(
    delivery_type: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    order_status: Optional[str] = Query(None),
    pickup_location_id: Optional[int] = Query(None),
    delivery_boy_id: Optional[int] = Query(None),
    assigned: Optional[str] = Query(None),   # "yes" | "no"
    payment_method: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),  # ISO date string YYYY-MM-DD
    date_to: Optional[str] = Query(None),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    List all orders with rich filtering:
    delivery_type, payment_status, order_status, pickup_location_id,
    delivery_boy_id, assigned (yes/no), payment_method, date_from, date_to.
    """
    from datetime import datetime, timezone
    query = db.query(Order)

    if delivery_type:
        query = query.filter(Order.delivery_type == delivery_type)
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    if order_status:
        query = query.filter(Order.order_status == order_status)
    if pickup_location_id:
        query = query.filter(Order.pickup_location_id == pickup_location_id)
    if delivery_boy_id:
        query = query.filter(Order.delivery_boy_id == delivery_boy_id)
    if assigned == "yes":
        query = query.filter(Order.delivery_boy_id.isnot(None))
    elif assigned == "no":
        query = query.filter(Order.delivery_boy_id.is_(None))
    if payment_method:
        query = query.filter(Order.payment_method == payment_method)
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(Order.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            query = query.filter(Order.created_at <= dt_to)
        except ValueError:
            pass

    orders = query.order_by(Order.created_at.desc()).all()

    result = []
    for o in orders:
        items = [
            {
                "variant": (
                    f"{i.product_variant.product.name} – {i.product_variant.size_name}"
                    if i.product_variant and i.product_variant.product else "—"
                ),
                "qty": i.quantity,
                "unit_price": str(i.unit_price),
                "subtotal": str(i.subtotal),
            }
            for i in o.order_items
        ]
        result.append({
            "id": o.id,
            "order_ref": o.order_ref,
            "customer_name": o.customer_name,
            "customer_email": o.customer_email,
            "customer_phone": o.customer_phone,
            "delivery_type": o.delivery_type,
            "delivery_address": o.delivery_address,
            "pickup_location_id": o.pickup_location_id,
            "pickup_location_name": o.pickup_location.name if o.pickup_location else None,
            "order_status": o.order_status,
            "payment_status": o.payment_status,
            "payment_method": o.payment_method,
            "subtotal": str(o.subtotal),
            "delivery_fee": str(o.delivery_fee),
            "total_price": str(o.total_price),
            "delivery_boy_id": o.delivery_boy_id,
            "delivery_boy_name": o.delivery_boy.full_name or o.delivery_boy.username if o.delivery_boy else None,
            "delivery_code": o.delivery_code,
            "assigned_at": o.assigned_at.isoformat() if o.assigned_at else None,
            "customer_notes": o.customer_notes,
            "shipment_id": o.shipment_id,
            "booked_by_admin_id": o.booked_by_admin_id,
            "booked_by_admin_name": o.booked_by_admin_name,
            "items": items,
            "items_count": len(items),
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
    return result


@router.get("/orders/null-shipment-count")
def get_null_shipment_order_count(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Return count of orders (delivery type) with no shipment linked."""
    count = db.query(Order).filter(
        Order.delivery_type == "delivery",
        Order.shipment_id.is_(None),
    ).count()
    return {"count": count}


@router.post("/orders/bulk-shipment")
def bulk_assign_order_shipment(
    payload: OrderBulkShipmentIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Assign a shipment to multiple orders in one call.
    - If order_ids provided: assign only those orders.
    - If order_ids is None and only_null=True: assign all delivery orders with null shipment_id.
    - If order_ids is None and only_null=False: assign ALL delivery orders (overwrite existing).
    """
    from database.models import Shipment as ShipmentModel
    shipment = db.query(ShipmentModel).filter(ShipmentModel.id == payload.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {payload.shipment_id} not found")

    query = db.query(Order).filter(Order.delivery_type == "delivery")
    if payload.order_ids:
        query = query.filter(Order.id.in_(payload.order_ids))
    elif payload.only_null:
        query = query.filter(Order.shipment_id.is_(None))

    orders = query.all()
    for o in orders:
        o.shipment_id = payload.shipment_id
    db.commit()
    return {
        "updated": [o.id for o in orders],
        "count": len(orders),
        "shipment_id": payload.shipment_id,
        "shipment_ref": shipment.shipment_ref,
    }


@router.put("/orders/{order_id}/shipment")
def update_order_shipment(
    order_id: int,
    payload: OrderShipmentUpdate,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Admin: change or clear the shipment linked to an order."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if payload.shipment_id is not None:
        from database.models import Shipment
        if not db.query(Shipment).filter(Shipment.id == payload.shipment_id).first():
            raise HTTPException(status_code=404, detail=f"Shipment {payload.shipment_id} not found")
    order.shipment_id = payload.shipment_id
    db.commit()
    return {"order_id": order_id, "shipment_id": order.shipment_id}


@router.put("/orders/bulk-status")
def bulk_update_order_status(
    payload: OrderBulkStatusIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Bulk-update order_status for a list of orders and write an audit log entry per order."""
    updated = []
    for order_id in payload.order_ids:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            continue
        log = OrderStatusLog(
            order_id=order_id,
            old_status=order.order_status,
            new_status=payload.new_status,
            changed_by=current_admin.id,
            note=payload.note,
        )
        db.add(log)
        order.order_status = payload.new_status
        updated.append(order_id)
    db.commit()
    return {
        "updated": updated,
        "new_status": payload.new_status,
        "changed_by": current_admin.username,
        "count": len(updated),
    }


@router.put("/orders/{order_id}/collect-payment")
def collect_pay_later_payment(
    order_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Mark a pay_later order's payment as collected (succeeded)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.payment_method != "pay_later":
        raise HTTPException(status_code=400, detail="This endpoint is only for pay_later orders")
    if order.payment_status == "succeeded":
        raise HTTPException(status_code=409, detail="Payment already marked as collected")
    order.payment_status = "succeeded"
    db.commit()
    return {
        "order_id": order.id,
        "order_ref": order.order_ref,
        "payment_status": order.payment_status,
        "message": "Payment marked as collected",
    }


@router.post("/delivery-boys/{delivery_boy_id}/assign")
def assign_orders_to_delivery_boy(
    delivery_boy_id: int,
    payload: AssignDeliveryIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Assign orders to a delivery boy and generate daily delivery code."""
    from datetime import datetime, timezone

    boy = db.query(DeliveryBoy).filter(DeliveryBoy.id == delivery_boy_id, DeliveryBoy.is_active == 1).first()
    if not boy:
        raise HTTPException(status_code=404, detail="Delivery boy not found")

    delivery_code = f"{boy.username}_{payload.delivery_date.strftime('%Y%m%d')}"
    now = datetime.now(timezone.utc)

    updated = []
    for order_id in payload.order_ids:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            continue
        order.delivery_boy_id = delivery_boy_id
        order.delivery_code   = delivery_code
        order.assigned_at     = now
        updated.append(order_id)

    db.commit()
    return {"assigned": updated, "delivery_code": delivery_code}

