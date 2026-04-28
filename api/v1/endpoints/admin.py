from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload, joinedload

from database.connection import get_db
from database.models import AdminUser, DeliveryBoy, DeliveryTag, Order, OrderActionLog, OrderActionType, OrderItem, OrderStatusLog, Pricing, ProductVariant, User
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
    DeliveryTagIn, DeliveryTagOut, DeliveryTagUpdate, OrderBulkTagIn,
)
from services.order_action_service import log_order_action as _log_order_action
from services.admin_service import (
    create_spoc_contact, get_spoc_contact, get_all_spoc_contacts,
    create_shipment, get_shipment, get_shipment_by_ref, get_all_shipments, update_shipment,
    add_box_to_shipment, get_shipment_box, update_shipment_box,
    log_delivery, get_delivery_logs,
    generate_shipment_summary, get_shipment_summary, get_dashboard_summary,
    # New functions
    create_pickup_location, get_all_pickup_locations, get_pickup_location, update_pickup_location, delete_pickup_location, get_location_occupancy,
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
        full_name=user.full_name,
        email=user.email,
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
    query = db.query(Order).options(
        selectinload(Order.order_items)
            .joinedload(OrderItem.product_variant)
            .joinedload(ProductVariant.product),
        joinedload(Order.pickup_location),
        joinedload(Order.delivery_boy),
    ).filter(Order.shipment_id == shipment_id)
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
                "product_variant_id": i.product_variant_id,
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
            "pickup_location_address": o.pickup_location.address if o.pickup_location else None,
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


@router.delete("/pickup-locations/{location_id}", status_code=204)
def delete_location(
    location_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a pickup location."""
    delete_pickup_location(db, location_id)


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
        .options(selectinload(Order.order_items))
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
        .options(
            selectinload(Order.order_items),
            joinedload(Order.delivery_boy),
        )
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
    tag_id: Optional[str] = Query(None),     # numeric id or "untagged"
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    List all orders with rich filtering:
    delivery_type, payment_status, order_status, pickup_location_id,
    delivery_boy_id, assigned (yes/no), payment_method, date_from, date_to.
    """
    from datetime import datetime, timezone
    query = db.query(Order).options(
        selectinload(Order.order_items)
            .joinedload(OrderItem.product_variant)
            .joinedload(ProductVariant.product),
        joinedload(Order.pickup_location),
        joinedload(Order.delivery_boy),
    )

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
    if tag_id == "untagged":
        query = query.filter(Order.delivery_tag_id.is_(None))
    elif tag_id:
        try:
            query = query.filter(Order.delivery_tag_id == int(tag_id))
        except ValueError:
            pass
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
                "product_variant_id": i.product_variant_id,
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
            "pickup_location_address": o.pickup_location.address if o.pickup_location else None,
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
            "delivery_tag_id": o.delivery_tag_id,
            "delivery_tag_name": o.delivery_tag.name if o.delivery_tag else None,
            "delivery_tag_color": o.delivery_tag.color if o.delivery_tag else None,
            "actual_price": float(o.actual_price) if o.actual_price is not None else None,
            "payment_comments": o.payment_comments,
            "payment_received_by": o.payment_received_by,
            "payment_updated_by": o.payment_updated_by,
            "payment_collection_status": o.payment_collection_status or "to_be_received",
            "items": items,
            "items_count": len(items),
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
    return result


@router.get("/orders/abandoned-checkouts", response_model=list[dict])
def get_abandoned_checkouts(
    minutes: int = Query(15, ge=1, le=1440),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Return orders where payment was initiated (paynow) but never completed,
    created more than `minutes` minutes ago.
    Excludes pay_later orders (those are legitimate admin-booked orders).
    """
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    orders = (
        db.query(Order)
        .filter(
            Order.payment_method == "paynow",
            Order.payment_status == "pending",
            Order.created_at <= cutoff,
        )
        .order_by(Order.created_at.desc())
        .all()
    )
    result = []
    for o in orders:
        items = [
            {
                "product_variant_id": i.product_variant_id,
                "variant": (
                    f"{i.product_variant.product.name} – {i.product_variant.size_name}"
                    if i.product_variant and i.product_variant.product else "—"
                ),
                "qty": i.quantity,
                "unit_price": str(i.unit_price),
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
            "total_price": str(o.total_price),
            "items": items,
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
    # Google OAuth admins have an id from the users table, not admin_users — don't FK it
    admin_user_id = current_admin.id if isinstance(current_admin, AdminUser) else None

    updated = []
    for order_id in payload.order_ids:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            continue
        log = OrderStatusLog(
            order_id=order_id,
            old_status=order.order_status,
            new_status=payload.new_status,
            changed_by=admin_user_id,
            note=payload.note,
        )
        db.add(log)
        _log_order_action(db, order_id, "STATUS_UPDATE", current_admin,
                          details={"old": order.order_status, "new": payload.new_status},
                          note=payload.note)
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
    _log_order_action(db, order_id, "PAYMENT_COLLECTED", current_admin,
                      details={"payment_method": order.payment_method})
    db.commit()
    return {
        "order_id": order.id,
        "order_ref": order.order_ref,
        "payment_status": order.payment_status,
        "message": "Payment marked as collected",
    }


from pydantic import BaseModel as _BM
from datetime import date as _date
from sqlalchemy import or_ as _or
class _ItemEdit(_BM):
    product_variant_id: Optional[int] = None
    quantity: int

class _OrderEditIn(_BM):
    customer_name:      Optional[str] = None
    customer_email:     Optional[str] = None
    customer_phone:     Optional[str] = None
    delivery_address:   Optional[str] = None
    customer_notes:     Optional[str] = None
    order_status:       Optional[str] = None
    payment_status:     Optional[str] = None   # 'pending' | 'succeeded' | 'failed' | 'cancelled'
    delivery_type:      Optional[str] = None   # 'delivery' | 'pickup'
    pickup_location_id: Optional[int] = None
    items:              Optional[List[_ItemEdit]] = None


@router.patch("/orders/{order_id}")
def admin_update_order(
    order_id: int,
    body: _OrderEditIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Admin: update order fields and/or replace order items."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # ── snapshot before update ──
    _pre_customer = {
        "customer_name":  order.customer_name,
        "customer_email": order.customer_email,
        "customer_phone": order.customer_phone,
    }
    _pre_delivery = {
        "delivery_address":   order.delivery_address,
        "delivery_type":      order.delivery_type,
        "pickup_location_id": order.pickup_location_id,
    }
    _pre_order_status   = order.order_status
    _pre_payment_status = order.payment_status
    _pre_notes          = order.customer_notes

    # snapshot items with names BEFORE deletion (lazy-load while session is clean)
    _pre_items_map: dict = {}
    if body.items is not None:
        for it in order.order_items:
            pv = it.product_variant
            if pv:
                prod_name = pv.product.name if pv.product else f"Variant #{it.product_variant_id}"
                size = pv.size_name
                label = prod_name if not size or size.lower() == "standard" else f"{prod_name} ({size})"
            else:
                label = f"Variant #{it.product_variant_id}"
            _pre_items_map[it.product_variant_id] = {"name": label, "qty": it.quantity}

    # ── update simple fields ──
    if body.customer_name      is not None: order.customer_name      = body.customer_name
    if body.customer_email     is not None: order.customer_email     = body.customer_email
    if body.customer_phone     is not None: order.customer_phone     = body.customer_phone
    if body.delivery_address   is not None: order.delivery_address   = body.delivery_address
    if body.customer_notes     is not None: order.customer_notes     = body.customer_notes
    if body.order_status       is not None: order.order_status       = body.order_status
    if body.payment_status     is not None: order.payment_status     = body.payment_status
    if body.delivery_type      is not None: order.delivery_type      = body.delivery_type
    if body.pickup_location_id is not None: order.pickup_location_id = body.pickup_location_id

    # ── replace items ──
    _post_items_map: dict = {}
    if body.items is not None:
        db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()
        db.flush()

        today = _date.today()
        subtotal = 0.0
        for it in body.items:
            if it.quantity <= 0:
                continue
            variant = db.query(ProductVariant).filter(ProductVariant.id == it.product_variant_id).first()
            if not variant:
                continue
            # build post-snapshot entry while variant is already in scope
            pv_prod_name = variant.product.name if variant.product else f"Variant #{it.product_variant_id}"
            pv_size = variant.size_name
            pv_label = pv_prod_name if not pv_size or pv_size.lower() == "standard" else f"{pv_prod_name} ({pv_size})"
            _post_items_map[it.product_variant_id] = {"name": pv_label, "qty": it.quantity}
            # resolve active price
            pricing = (
                db.query(Pricing)
                .filter(
                    Pricing.product_variant_id == variant.id,
                    _or(Pricing.valid_from == None, Pricing.valid_from <= today),
                    _or(Pricing.valid_to == None,   Pricing.valid_to   >= today),
                )
                .first()
            )
            if not pricing:
                pricing = db.query(Pricing).filter(Pricing.product_variant_id == variant.id).first()
            unit_price = float(pricing.base_price) if pricing else 0.0
            line_subtotal = unit_price * it.quantity
            subtotal += line_subtotal
            db.add(OrderItem(
                order_id=order_id,
                product_variant_id=it.product_variant_id,
                quantity=it.quantity,
                unit_price=unit_price,
                subtotal=line_subtotal,
            ))

        order.subtotal    = subtotal
        order.total_price = subtotal + float(order.delivery_fee or 0)

    # ── detect changes and write action logs ──
    _changed_customer = {
        k: {"old": _pre_customer[k], "new": getattr(order, k)}
        for k in _pre_customer
        if getattr(order, k) != _pre_customer[k]
    }
    if _changed_customer:
        _log_order_action(db, order_id, "CUSTOMER_INFO_UPDATE", current_admin, details=_changed_customer)

    _changed_delivery = {
        k: {"old": _pre_delivery[k], "new": getattr(order, k)}
        for k in _pre_delivery
        if getattr(order, k) != _pre_delivery[k]
    }
    if _changed_delivery:
        _log_order_action(db, order_id, "DELIVERY_UPDATE", current_admin, details=_changed_delivery)

    if order.order_status != _pre_order_status:
        _log_order_action(db, order_id, "STATUS_UPDATE", current_admin,
                          details={"old": _pre_order_status, "new": order.order_status})

    if order.payment_status != _pre_payment_status:
        _log_order_action(db, order_id, "PAYMENT_UPDATE", current_admin,
                          details={"old": _pre_payment_status, "new": order.payment_status})

    if order.customer_notes != _pre_notes and body.customer_notes is not None:
        _log_order_action(db, order_id, "NOTES_UPDATED", current_admin,
                          details={"old": _pre_notes, "new": order.customer_notes})

    if body.items is not None:
        _added, _removed, _changed = [], [], []
        for vid in set(_pre_items_map) | set(_post_items_map):
            pre  = _pre_items_map.get(vid)
            post = _post_items_map.get(vid)
            if pre and not post:
                _removed.append(pre["name"])
            elif not pre and post:
                _added.append(f"{post['name']} ×{post['qty']}")
            elif pre and post and pre["qty"] != post["qty"]:
                _changed.append({"name": pre["name"], "old": pre["qty"], "new": post["qty"]})
        _items_diff = {k: v for k, v in {"added": _added, "removed": _removed, "changed": _changed}.items() if v}
        if _items_diff:
            _log_order_action(db, order_id, "ITEMS_UPDATED", current_admin, details=_items_diff)

    db.commit()
    db.refresh(order)
    return {
        "success": True,
        "order_id": order.id,
        "order_ref": order.order_ref,
        "order_status": order.order_status,
        "subtotal": float(order.subtotal),
        "total_price": float(order.total_price),
    }


class _PaymentDetailIn(_BM):
    actual_price:              Optional[float] = None
    payment_comments:          Optional[str]   = None
    payment_received_by:       Optional[str]   = None
    payment_collection_status: Optional[str]   = None  # 'to_be_received' | 'received'


@router.patch("/orders/{order_id}/payment-details")
def update_order_payment_details(
    order_id: int,
    body: _PaymentDetailIn,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Save payment detail fields (actual price, comments, received-by, collection status)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    _pre = {
        "actual_price":              float(order.actual_price) if order.actual_price is not None else None,
        "payment_comments":          order.payment_comments,
        "payment_received_by":       order.payment_received_by,
        "payment_collection_status": order.payment_collection_status,
    }

    if body.actual_price is not None:
        order.actual_price = body.actual_price
    if body.payment_comments is not None:
        order.payment_comments = body.payment_comments

    # Determine the effective received_by after this update
    effective_received_by = body.payment_received_by if body.payment_received_by is not None else order.payment_received_by
    if body.payment_received_by is not None:
        order.payment_received_by = body.payment_received_by

    if body.payment_collection_status is not None:
        if body.payment_collection_status == "received" and effective_received_by:
            # Direct identifiers from admin_users (username, full_name, email)
            caller_identifiers = {
                v for v in [
                    getattr(current_admin, "username", None),
                    getattr(current_admin, "full_name", None),
                    getattr(current_admin, "email", None),
                ] if v
            }
            is_self = effective_received_by in caller_identifiers
            # Cross-table check: find the recipient in users table and compare by email
            if not is_self and getattr(current_admin, "email", None):
                target_user = (
                    db.query(User)
                    .filter(User.name == effective_received_by, User.role == "admin")
                    .first()
                )
                if target_user and target_user.email == current_admin.email:
                    is_self = True
            if not is_self:
                raise HTTPException(
                    status_code=403,
                    detail="Only the assigned recipient can mark payment as 'Received'.",
                )
        order.payment_collection_status = body.payment_collection_status

    order.payment_updated_by = (
        getattr(current_admin, "username", None)
        or getattr(current_admin, "name", None)
        or "admin"
    )

    _diff = {
        k: {"old": _pre[k], "new": getattr(order, k)}
        for k in _pre
        if str(getattr(order, k) or "") != str(_pre[k] or "")
    }
    if _diff:
        _log_order_action(db, order_id, "PAYMENT_UPDATE", current_admin, details=_diff)

    db.commit()
    return {
        "success":                  True,
        "order_id":                 order.id,
        "actual_price":             float(order.actual_price) if order.actual_price is not None else None,
        "payment_comments":         order.payment_comments,
        "payment_received_by":      order.payment_received_by,
        "payment_updated_by":       order.payment_updated_by,
        "payment_collection_status": order.payment_collection_status or "to_be_received",
    }


@router.get("/orders/{order_id}/history", response_model=list[dict])
def get_order_history(
    order_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Return a chronological audit trail for a single order."""
    from sqlalchemy import text as _text
    import json as _json

    events = []

    # ── Audit log (Oracle trigger-based) ──
    try:
        rows = db.execute(
            _text("""
                SELECT operation, changed_by, changed_at, old_values, new_values
                FROM audit_log
                WHERE table_name = 'ORDERS' AND record_id = :oid
                ORDER BY changed_at ASC
            """),
            {"oid": order_id},
        ).fetchall()
        for r in rows:
            old_v = r.old_values
            new_v = r.new_values
            if hasattr(old_v, "read"): old_v = old_v.read()
            if hasattr(new_v, "read"): new_v = new_v.read()
            try:
                old_v = _json.loads(old_v) if old_v else {}
            except Exception:
                old_v = {"raw": str(old_v)}
            try:
                new_v = _json.loads(new_v) if new_v else {}
            except Exception:
                new_v = {"raw": str(new_v)}
            ts = r.changed_at
            events.append({
                "source":     "audit",
                "operation":  r.operation,
                "changed_by": r.changed_by or "system",
                "changed_at": ts.isoformat() if ts else None,
                "old_values": old_v,
                "new_values": new_v,
            })
    except Exception:
        pass  # audit_log may not exist in all environments

    # ── OrderStatusLog (application-level) ──
    status_logs = (
        db.query(OrderStatusLog)
        .filter(OrderStatusLog.order_id == order_id)
        .order_by(OrderStatusLog.changed_at.asc())
        .all()
    )
    for sl in status_logs:
        admin_name = sl.admin_user.username if sl.admin_user else "admin"
        ts = sl.changed_at
        events.append({
            "source":     "status_log",
            "operation":  "STATUS_CHANGE",
            "changed_by": admin_name,
            "changed_at": ts.isoformat() if ts else None,
            "old_values": {"order_status": sl.old_status},
            "new_values": {"order_status": sl.new_status},
            "note":       sl.note or "",
        })

    events.sort(key=lambda x: x["changed_at"] or "")
    return events


@router.get("/order-action-types", response_model=list[dict])
def list_order_action_types(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Return all active order action type definitions (config table)."""
    types = (
        db.query(OrderActionType)
        .filter(OrderActionType.is_active == 1)
        .order_by(OrderActionType.sort_order)
        .all()
    )
    return [
        {
            "id":          t.id,
            "code":        t.code,
            "label":       t.label,
            "description": t.description,
            "color":       t.color,
            "icon":        t.icon,
        }
        for t in types
    ]


@router.get("/orders/{order_id}/action-logs", response_model=list[dict])
def get_order_action_logs(
    order_id: int,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Return the chronological action log for a single order."""
    logs = (
        db.query(OrderActionLog)
        .filter(OrderActionLog.order_id == order_id)
        .order_by(OrderActionLog.created_at.asc())
        .all()
    )
    result = []
    for log in logs:
        details_parsed = None
        if log.details:
            try:
                raw = log.details
                if hasattr(raw, "read"):
                    raw = raw.read()
                details_parsed = _json.loads(raw) if raw else None
            except Exception:
                details_parsed = {"raw": str(log.details)}

        atype = log.action_type
        ts = log.created_at
        result.append({
            "id":           log.id,
            "order_id":     log.order_id,
            "action_type":  {
                "code":  atype.code,
                "label": atype.label,
                "color": atype.color,
                "icon":  atype.icon,
            } if atype else None,
            "performed_by": log.performed_by or "system",
            "details":      details_parsed,
            "note":         log.note,
            "created_at":   ts.isoformat() if ts else None,
        })
    return result


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



# ============================================================================
# Customer Users List (for promo assignment etc.)
# ============================================================================

@router.get("/users", tags=["admin"])
def list_customer_users(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Return all registered customer users (admin only)."""
    users = db.query(User).order_by(User.name).all()
    return [{"id": u.id, "name": u.name, "email": u.email} for u in users]


@router.get("/admin-users-list", tags=["admin"])
def list_admin_users(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Return all admin-role users from the users table — used for the payment 'received by' dropdown."""
    users = (
        db.query(User)
        .filter(User.role == 'admin')
        .order_by(User.name)
        .all()
    )
    my_emails = {v for v in [current_admin.email] if v}

    result = []
    me_found = False
    for u in users:
        is_me = bool(u.email and u.email in my_emails)
        if is_me:
            me_found = True
        result.append({
            "id": u.id,
            "name": u.name or u.email,
            "username": u.name or u.email,
            "email": u.email,
            "is_me": is_me,
        })

    # If the logged-in admin is not found in the users table via email,
    # inject their own entry so they can always select themselves.
    if not me_found:
        my_display_name = current_admin.full_name or current_admin.username
        result.insert(0, {
            "id": f"admin_{current_admin.id}",
            "name": my_display_name,
            "username": my_display_name,
            "email": current_admin.email,
            "is_me": True,
        })

    return result


# ============================================================================
# DELIVERY TAGS
# ============================================================================

@router.get("/delivery-tags", response_model=List[DeliveryTagOut])
def list_delivery_tags(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    return db.query(DeliveryTag).order_by(DeliveryTag.name).all()


@router.post("/delivery-tags", response_model=DeliveryTagOut, status_code=201)
def create_delivery_tag(
    payload: DeliveryTagIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    existing = db.query(DeliveryTag).filter(DeliveryTag.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="A tag with this name already exists")
    tag = DeliveryTag(
        name=payload.name,
        color=payload.color or "#6b7280",
        price=payload.price,
        is_active=payload.is_active if payload.is_active is not None else 1,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.patch("/delivery-tags/{tag_id}", response_model=DeliveryTagOut)
def update_delivery_tag(
    tag_id: int,
    payload: DeliveryTagUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    tag = db.query(DeliveryTag).filter(DeliveryTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if payload.price is not None:
        tag.price = payload.price
    if payload.is_active is not None:
        tag.is_active = payload.is_active
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/delivery-tags/{tag_id}", status_code=204)
def delete_delivery_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    tag = db.query(DeliveryTag).filter(DeliveryTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    # Clear the tag from any assigned orders first
    db.query(Order).filter(Order.delivery_tag_id == tag_id).update({"delivery_tag_id": None})
    db.delete(tag)
    db.commit()


@router.put("/orders/bulk-tag")
def bulk_assign_delivery_tag(
    payload: OrderBulkTagIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Assign (or clear) a delivery tag on a list of orders."""
    if payload.tag_id is not None:
        tag = db.query(DeliveryTag).filter(DeliveryTag.id == payload.tag_id).first()
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
    updated = []
    for order_id in payload.order_ids:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            continue
        order.delivery_tag_id = payload.tag_id
        updated.append(order_id)
    db.commit()
    return {"updated": updated, "tag_id": payload.tag_id, "count": len(updated)}
