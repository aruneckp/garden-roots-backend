import random
import string
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.models import (
    AdminUser, SPOCContact, Shipment, ShipmentBox, DeliveryLog, ShipmentSummary, Product, ProductVariant
)
from schemas.admin import (
    AdminLoginIn, AdminTokenOut, SPOCContactIn, SPOCContactOut,
    ShipmentIn, ShipmentOut, ShipmentDetailOut, ShipmentUpdate,
    ShipmentBoxIn, ShipmentBoxOut, ShipmentBoxUpdate,
    DeliveryLogIn, DeliveryLogOut,
    ShipmentSummaryOut, ShipmentConsolidatedSummary,
    ShipmentVarietyOut,
)


def _generate_shipment_ref() -> str:
    """Generate unique shipment reference."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"SHP-{suffix}"


def _calc_order_stats(orders: list) -> dict:
    """Compute order status breakdown from a list of Order objects."""
    total = len(orders)
    booked       = sum(1 for o in orders if o.order_status in ("confirmed", "processing"))
    pending      = sum(1 for o in orders if o.order_status == "pending")
    in_transit   = sum(1 for o in orders if o.order_status == "in_transit")
    delivered    = sum(1 for o in orders if o.order_status == "delivered")
    cancelled    = sum(1 for o in orders if o.order_status == "cancelled")
    yet_to_book  = sum(1 for o in orders if o.order_status not in ("confirmed", "processing", "in_transit", "delivered", "cancelled"))
    return {
        "orders_total":      total,
        "orders_booked":     booked,
        "orders_pending":    pending,
        "orders_in_transit": in_transit,
        "orders_delivered":  delivered,
        "orders_cancelled":  cancelled,
        "orders_yet_to_book": yet_to_book,
    }


# ============================================================================
# SPOC Contact Functions
# ============================================================================

def create_spoc_contact(db: Session, payload: SPOCContactIn) -> SPOCContactOut:
    """Create a new SPOC contact."""
    contact = SPOCContact(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        location=payload.location,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return SPOCContactOut.model_validate(contact)


def get_spoc_contact(db: Session, contact_id: int) -> SPOCContactOut:
    """Get SPOC contact by ID."""
    contact = db.query(SPOCContact).filter(SPOCContact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail=f"SPOC contact {contact_id} not found")
    return SPOCContactOut.model_validate(contact)


def get_all_spoc_contacts(db: Session) -> List[SPOCContactOut]:
    """Get all SPOC contacts."""
    contacts = db.query(SPOCContact).all()
    return [SPOCContactOut.model_validate(c) for c in contacts]


# ============================================================================
# Shipment Management Functions
# ============================================================================

def create_shipment(db: Session, payload: ShipmentIn) -> ShipmentOut:
    """Create a new shipment with one or more mango variety entries."""
    if not payload.varieties and not payload.product_id:
        raise HTTPException(status_code=400, detail="At least one variety or a product_id is required")

    # Determine the primary product_id (use first variety's product if not explicitly set)
    primary_product_id = payload.product_id or payload.varieties[0].product_id

    primary_product = db.query(Product).filter(Product.id == primary_product_id).first()
    if not primary_product:
        raise HTTPException(status_code=404, detail=f"Product {primary_product_id} not found")

    # Total boxes = sum of all variety box counts (or payload value if no varieties)
    total_boxes = sum(v.box_count for v in payload.varieties) if payload.varieties else payload.total_boxes

    shipment = Shipment(
        shipment_ref=_generate_shipment_ref(),
        product_id=primary_product_id,
        total_boxes=total_boxes,
        expected_value=payload.expected_value,
        spoc_contact_id=payload.spoc_contact_id,
        notes=payload.notes,
        status="pending",
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    # Create one ShipmentBox entry per variety using product name as variety_size
    if payload.varieties:
        for variety in payload.varieties:
            variety_product = db.query(Product).filter(Product.id == variety.product_id).first()
            if not variety_product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product (variety) {variety.product_id} not found",
                )
            box = ShipmentBox(
                shipment_id=shipment.id,
                box_number=f"VAR-{variety_product.name.replace(' ', '-').upper()}",
                quantity_boxes=variety.box_count,
                variety_size=variety_product.name,
                product_variant_id=None,
                delivery_type="pending",
                delivery_charge=0.0,
                box_weight=variety.box_weight,
                price_per_kg=variety.price_per_kg,
            )
            db.add(box)
        db.commit()
        db.refresh(shipment)

    out = ShipmentOut.model_validate(shipment)
    out.variety_names = [box.variety_size for box in shipment.boxes if box.variety_size]
    return out


def get_shipment(db: Session, shipment_id: int) -> ShipmentDetailOut:
    """Get shipment details by ID."""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    out = ShipmentDetailOut.model_validate(shipment)
    variety_map = {}
    for box in shipment.boxes:
        if box.product_variant_id and box.variety_size:
            key = box.product_variant_id
            if key not in variety_map:
                variety_map[key] = ShipmentVarietyOut(
                    product_variant_id=box.product_variant_id,
                    variety_name=box.variety_size,
                    box_count=0,
                )
            variety_map[key].box_count += box.quantity_boxes
    out.varieties = list(variety_map.values())
    return out


def get_shipment_by_ref(db: Session, shipment_ref: str) -> ShipmentDetailOut:
    """Get shipment details by reference."""
    shipment = db.query(Shipment).filter(Shipment.shipment_ref == shipment_ref).first()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_ref} not found")
    return get_shipment(db, shipment.id)


def get_all_shipments(db: Session, status: Optional[str] = None) -> List[ShipmentOut]:
    """Get all shipments, optionally filtered by status."""
    query = db.query(Shipment)
    if status:
        query = query.filter(Shipment.status == status)
    shipments = query.order_by(Shipment.created_at.desc()).all()
    result = []
    for s in shipments:
        out = ShipmentOut.model_validate(s)
        out.variety_names = list({box.variety_size for box in s.boxes if box.variety_size})
        result.append(out)
    return result


def update_shipment(db: Session, shipment_id: int, payload: ShipmentUpdate) -> ShipmentDetailOut:
    """Update shipment details."""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    if payload.status:
        if payload.status == "completed":
            shipment.completion_date = datetime.now(timezone.utc)
        shipment.status = payload.status

    if payload.spoc_contact_id:
        shipment.spoc_contact_id = payload.spoc_contact_id

    if payload.notes:
        shipment.notes = payload.notes

    db.commit()
    db.refresh(shipment)
    return ShipmentDetailOut.model_validate(shipment)


# ============================================================================
# Shipment Box Functions
# ============================================================================

def add_box_to_shipment(db: Session, shipment_id: int, payload: ShipmentBoxIn) -> ShipmentBoxOut:
    """Add a box to a shipment."""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    box = ShipmentBox(
        shipment_id=shipment_id,
        box_number=payload.box_number,
        quantity_boxes=payload.quantity_boxes,
        delivery_type=payload.delivery_type,
        delivery_charge=payload.delivery_charge,
    )
    db.add(box)
    db.commit()
    db.refresh(box)
    return ShipmentBoxOut.model_validate(box)


def get_shipment_box(db: Session, box_id: int) -> ShipmentBoxOut:
    """Get box details."""
    box = db.query(ShipmentBox).filter(ShipmentBox.id == box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail=f"Box {box_id} not found")
    return ShipmentBoxOut.model_validate(box)


def update_shipment_box(db: Session, box_id: int, payload: ShipmentBoxUpdate) -> ShipmentBoxOut:
    """Update box status and delivery details."""
    box = db.query(ShipmentBox).filter(ShipmentBox.id == box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail=f"Box {box_id} not found")

    if payload.box_status:
        box.box_status = payload.box_status

    if payload.delivery_type:
        box.delivery_type = payload.delivery_type

    if payload.delivery_charge is not None:
        box.delivery_charge = payload.delivery_charge

    db.commit()
    db.refresh(box)
    return ShipmentBoxOut.model_validate(box)


# ============================================================================
# Delivery Log Functions
# ============================================================================

def log_delivery(db: Session, shipment_box_id: int, payload: DeliveryLogIn) -> DeliveryLogOut:
    """Log delivery of a box."""
    box = db.query(ShipmentBox).filter(ShipmentBox.id == shipment_box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail=f"Box {shipment_box_id} not found")

    log_entry = DeliveryLog(
        shipment_box_id=shipment_box_id,
        location_id=payload.location_id,
        order_id=payload.order_id,
        delivery_address=payload.delivery_address,
        delivery_notes=payload.delivery_notes,
        receiver_name=payload.receiver_name,
        receiver_phone=payload.receiver_phone,
        is_direct_delivery=int(payload.is_direct_delivery),
        delivery_date=datetime.now(timezone.utc),
    )

    # Update box status
    if payload.is_direct_delivery:
        box.delivery_type = "direct-delivery"
        box.box_status = "delivered"
    else:
        box.delivery_type = "self-collection"
        box.box_status = "collected"

    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return DeliveryLogOut.model_validate(log_entry)


def get_delivery_logs(db: Session, shipment_id: int) -> List[DeliveryLogOut]:
    """Get all delivery logs for a shipment."""
    logs = db.query(DeliveryLog).join(ShipmentBox).filter(
        ShipmentBox.shipment_id == shipment_id
    ).all()
    return [DeliveryLogOut.model_validate(log) for log in logs]


# ============================================================================
# Shipment Summary/Reporting Functions
# ============================================================================

def generate_shipment_summary(db: Session, shipment_id: int) -> ShipmentConsolidatedSummary:
    """Generate consolidated summary for a shipment with proper defaults."""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    # Get all boxes for this shipment
    boxes = db.query(ShipmentBox).filter(ShipmentBox.shipment_id == shipment_id).all()

    # Count boxes by delivery type
    direct_delivery_count = sum(1 for b in boxes if b.delivery_type == "direct-delivery")
    self_collection_count = sum(1 for b in boxes if b.delivery_type == "self-collection")
    in_stock_count = sum(1 for b in boxes if b.box_status == "in-stock")
    damaged_count = sum(1 for b in boxes if b.box_status == "damaged")

    # Calculate total delivery revenue
    total_revenue = Decimal("0")

    # Get all delivery logs
    delivery_logs = db.query(DeliveryLog).join(ShipmentBox).filter(
        ShipmentBox.shipment_id == shipment_id
    ).all()

    for log in delivery_logs:
        box = next((b for b in boxes if b.id == log.shipment_box_id), None)
        if box and log.is_direct_delivery and box.delivery_charge:
            total_revenue += Decimal(str(box.delivery_charge))

    # Build delivery locations list
    delivery_locations = []
    location_summary_dict = {}

    # Process existing deliveries
    for log in delivery_logs:
        box = next((b for b in boxes if b.id == log.shipment_box_id), None)
        if not box:
            continue

        location_name = log.delivery_address or f"Location {log.location_id}" or "Warehouse"

        delivery_locations.append({
            "box_number": box.box_number,
            "delivery_type": "Direct Delivery" if log.is_direct_delivery else "Self Collection",
            "location": location_name,
            "receiver": log.receiver_name or "Receiver",
            "charge": float(box.delivery_charge) if log.is_direct_delivery else 0,
            "delivery_date": log.delivery_date.isoformat() if log.delivery_date else None,
            "phone": log.receiver_phone or "N/A"
        })

        # Aggregate by location
        if location_name not in location_summary_dict:
            location_summary_dict[location_name] = {
                "location": location_name,
                "boxes_count": 0,
                "direct_delivery_count": 0,
                "self_collection_count": 0,
                "total_revenue": 0,
                "receiver_count": 0
            }

        location_summary_dict[location_name]["boxes_count"] += 1
        if log.is_direct_delivery:
            location_summary_dict[location_name]["direct_delivery_count"] += 1
            location_summary_dict[location_name]["total_revenue"] += float(box.delivery_charge or 0)
        else:
            location_summary_dict[location_name]["self_collection_count"] += 1
        location_summary_dict[location_name]["receiver_count"] += 1

    summary_by_location = list(location_summary_dict.values())

    # Update or create summary record in database
    summary = db.query(ShipmentSummary).filter(ShipmentSummary.shipment_id == shipment_id).first()
    if not summary:
        summary = ShipmentSummary(shipment_id=shipment_id)
        db.add(summary)

    summary.total_boxes_received = len(boxes)
    summary.boxes_delivered_direct = direct_delivery_count
    summary.boxes_collected_self = self_collection_count
    summary.boxes_damaged = damaged_count
    summary.total_delivery_revenue = total_revenue
    summary.delivery_locations_count = len(location_summary_dict)

    db.commit()
    db.refresh(summary)

    # Build variety breakdown from boxes
    variety_map = {}
    for box in boxes:
        if box.product_variant_id and box.variety_size:
            key = box.variety_size
            if key not in variety_map:
                variety_map[key] = {
                    "variety_name": box.variety_size,
                    "product_variant_id": box.product_variant_id,
                    "box_count": 0,
                    "box_weight": float(box.box_weight) if box.box_weight is not None else None,
                    "price_per_kg": float(box.price_per_kg) if box.price_per_kg is not None else None,
                }
            variety_map[key]["box_count"] += box.quantity_boxes
    varieties_list = list(variety_map.values())

    return ShipmentConsolidatedSummary(
        shipment_ref=shipment.shipment_ref,
        total_boxes=len(boxes),
        boxes_delivered_direct=direct_delivery_count,
        boxes_collected_self=self_collection_count,
        boxes_damaged=damaged_count,
        total_delivery_revenue=float(total_revenue),
        delivery_locations=delivery_locations,
        spoc_contact=SPOCContactOut.model_validate(shipment.spoc_contact) if shipment.spoc_contact else None,
        summary_by_location=summary_by_location,
        varieties=varieties_list,
    )


def get_shipment_summary(db: Session, shipment_id: int) -> ShipmentConsolidatedSummary:
    """Get consolidated summary for a shipment."""
    return generate_shipment_summary(db, shipment_id)


def get_dashboard_summary(db: Session) -> dict:
    """Get overall dashboard summary across all shipments."""
    shipments = db.query(Shipment).all()

    total_shipments = len(shipments)
    completed_shipments = sum(1 for s in shipments if s.status == "completed")
    pending_shipments = sum(1 for s in shipments if s.status == "pending")
    in_transit_shipments = sum(1 for s in shipments if s.status == "in-transit")

    total_boxes = 0
    total_revenue = Decimal("0")
    all_summaries = []

    from database.models import Order

    for shipment in shipments:
        total_boxes += shipment.total_boxes

        orders = db.query(Order).filter(Order.shipment_id == shipment.id).all()
        order_stats = _calc_order_stats(orders)

        summary = db.query(ShipmentSummary).filter(ShipmentSummary.shipment_id == shipment.id).first()
        if summary:
            total_revenue += summary.total_delivery_revenue
        all_summaries.append({
            "shipment_id": shipment.id,
            "shipment_ref": shipment.shipment_ref,
            "total_boxes": shipment.total_boxes,
            "direct_delivery": summary.boxes_delivered_direct if summary else 0,
            "self_collection": summary.boxes_collected_self if summary else 0,
            "damaged": summary.boxes_damaged if summary else 0,
            "revenue": float(summary.total_delivery_revenue) if summary else 0.0,
            "status": shipment.status,
            **order_stats,
        })

    yet_to_book = db.query(Order).filter(
        Order.shipment_id.is_(None),
        Order.payment_status == "succeeded",
        Order.order_status != "cancelled",
    ).count()

    return {
        "total_shipments": total_shipments,
        "completed_shipments": completed_shipments,
        "pending_shipments": pending_shipments,
        "in_transit_shipments": in_transit_shipments,
        "total_boxes": total_boxes,
        "total_delivery_revenue": float(total_revenue),
        "yet_to_book_globally": yet_to_book,
        "shipment_summaries": all_summaries,
    }


def get_shipment_order_stats(db: Session, shipment_id: int) -> dict:
    """Return order status breakdown for a single shipment."""
    from database.models import Order, Shipment as ShipmentModel

    shipment = db.query(ShipmentModel).filter(ShipmentModel.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    orders = db.query(Order).filter(Order.shipment_id == shipment_id).all()
    stats = _calc_order_stats(orders)
    return {"shipment_id": shipment_id, "shipment_ref": shipment.shipment_ref, **stats}


# ============================================================================
# Pickup Location Management
# ============================================================================

def create_pickup_location(db: Session, location_data):
    """Create a new pickup location."""
    from database.models import PickupLocation

    location = PickupLocation(
        name=location_data.name,
        address=location_data.address,
        phone=location_data.phone,
        email=location_data.email,
        manager_name=location_data.manager_name,
        location_type=location_data.location_type,
        capacity=location_data.capacity,
        notes=location_data.notes,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def get_all_pickup_locations(db: Session):
    """Get all pickup locations."""
    from database.models import PickupLocation

    return db.query(PickupLocation).filter(PickupLocation.is_active == 1).all()


def get_pickup_location(db: Session, location_id: int):
    """Get pickup location by ID."""
    from database.models import PickupLocation

    location = db.query(PickupLocation).filter(PickupLocation.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Pickup location not found")
    return location


def update_pickup_location(db: Session, location_id: int, location_data):
    """Update pickup location."""
    from database.models import PickupLocation

    location = get_pickup_location(db, location_id)

    update_data = location_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    db.commit()
    db.refresh(location)
    return location


def get_location_occupancy(db: Session, location_id: int):
    """Get location occupancy and capacity information."""
    from database.models import PickupLocation, ShipmentBox

    location = get_pickup_location(db, location_id)

    boxes_stored = db.query(ShipmentBox).filter(
        ShipmentBox.location_id == location_id,
        ShipmentBox.delivery_status != "collected"
    ).count()

    occupancy_percentage = (boxes_stored / location.capacity * 100) if location.capacity > 0 else 0

    pending_boxes = db.query(ShipmentBox).filter(
        ShipmentBox.location_id == location_id,
        ShipmentBox.delivery_status == "pending"
    ).count()

    in_transit_boxes = db.query(ShipmentBox).filter(
        ShipmentBox.location_id == location_id,
        ShipmentBox.delivery_status == "in-transit"
    ).count()

    return {
        "location_id": location.id,
        "location_name": location.name,
        "location_type": location.location_type,
        "capacity": location.capacity,
        "boxes_stored": boxes_stored,
        "occupancy_percentage": round(occupancy_percentage, 2),
        "pending_boxes": pending_boxes,
        "in_transit_boxes": in_transit_boxes,
    }


# ============================================================================
# Prebooking Management
# ============================================================================

def create_prebooking(db: Session, prebooking_data):
    """Create a new prebooking for a box."""
    from database.models import Prebooking, ShipmentBox

    # Verify box exists
    box = db.query(ShipmentBox).filter(ShipmentBox.id == prebooking_data.shipment_box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail="Box not found")

    prebooking = Prebooking(
        shipment_id=prebooking_data.shipment_id,
        shipment_box_id=prebooking_data.shipment_box_id,
        customer_name=prebooking_data.customer_name,
        customer_phone=prebooking_data.customer_phone,
        customer_email=prebooking_data.customer_email,
        delivery_address=prebooking_data.delivery_address,
        scheduled_delivery_date=prebooking_data.scheduled_delivery_date,
        notes=prebooking_data.notes,
    )

    # Link prebooking to box
    box.prebooking_id = None  # Will be set after creation

    db.add(prebooking)
    db.commit()
    db.refresh(prebooking)

    # Update box with prebooking reference
    box.prebooking_id = prebooking.id
    box.delivery_type = "prebooking"
    box.receiver_name = prebooking.customer_name
    box.receiver_phone = prebooking.customer_phone
    db.commit()

    return prebooking


def get_prebookings_for_shipment(db: Session, shipment_id: int):
    """Get all prebookings for a shipment."""
    from database.models import Prebooking

    return db.query(Prebooking).filter(Prebooking.shipment_id == shipment_id).all()


def update_prebooking_status(db: Session, prebooking_id: int, status_data):
    """Update prebooking status."""
    from database.models import Prebooking

    prebooking = db.query(Prebooking).filter(Prebooking.id == prebooking_id).first()
    if not prebooking:
        raise HTTPException(status_code=404, detail="Prebooking not found")

    # Validate status transition
    valid_statuses = ["booked", "confirmed", "in-transit", "delivered", "cancelled"]
    if status_data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    prebooking.status = status_data.status
    if status_data.notes:
        prebooking.notes = status_data.notes

    db.commit()
    db.refresh(prebooking)
    return prebooking


# ============================================================================
# Payment Management
# ============================================================================

def record_payment(db: Session, payment_data):
    """Record a payment for a box."""
    from database.models import PaymentRecord, ShipmentBox, Shipment

    # Verify box exists
    box = db.query(ShipmentBox).filter(ShipmentBox.id == payment_data.shipment_box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail="Box not found")

    payment = PaymentRecord(
        shipment_box_id=payment_data.shipment_box_id,
        prebooking_id=payment_data.prebooking_id,
        description=payment_data.description,
        amount=payment_data.amount,
        payment_method=payment_data.payment_method,
        transaction_ref=payment_data.transaction_ref,
        notes=payment_data.notes,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Update box payment status
    update_box_payment_status(db, payment_data.shipment_box_id)

    return payment


def get_payment_summary(db: Session, shipment_id: int):
    """Get payment summary for a shipment."""
    from database.models import ShipmentBox, PaymentRecord

    records = db.query(PaymentRecord).join(
        ShipmentBox, ShipmentBox.id == PaymentRecord.shipment_box_id
    ).filter(ShipmentBox.shipment_id == shipment_id).all()

    pending_amount = sum(r.amount for r in records if r.payment_status == "pending")
    paid_amount = sum(r.amount for r in records if r.payment_status == "paid")
    total_amount = sum(r.amount for r in records)

    collection_percentage = (paid_amount / total_amount * 100) if total_amount > 0 else 0

    return {
        "total_payment_records": len(records),
        "pending_count": sum(1 for r in records if r.payment_status == "pending"),
        "paid_count": sum(1 for r in records if r.payment_status == "paid"),
        "pending_amount": pending_amount,
        "paid_amount": paid_amount,
        "total_amount": total_amount,
        "collection_percentage": round(collection_percentage, 2),
    }


def mark_payment_paid(db: Session, payment_id: int, update_data):
    """Mark a payment as paid."""
    from database.models import PaymentRecord
    from datetime import datetime, timezone

    payment = db.query(PaymentRecord).filter(PaymentRecord.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.payment_status = "paid"
    payment.payment_date = update_data.payment_date or datetime.now(timezone.utc)
    if update_data.payment_method:
        payment.payment_method = update_data.payment_method
    if update_data.transaction_ref:
        payment.transaction_ref = update_data.transaction_ref

    db.commit()
    db.refresh(payment)

    # Update box payment status
    update_box_payment_status(db, payment.shipment_box_id)

    return payment


def update_box_payment_status(db: Session, box_id: int):
    """Update box payment status based on payment records."""
    from database.models import ShipmentBox, PaymentRecord

    box = db.query(ShipmentBox).filter(ShipmentBox.id == box_id).first()
    if not box:
        return

    payment_records = db.query(PaymentRecord).filter(PaymentRecord.shipment_box_id == box_id).all()

    if not payment_records:
        box.payment_status = "pending"
    elif all(r.payment_status == "paid" for r in payment_records):
        box.payment_status = "paid"
    elif any(r.payment_status == "paid" for r in payment_records):
        box.payment_status = "partial"
    else:
        box.payment_status = "pending"

    db.commit()


# ============================================================================
# Box Entry and Status Management
# ============================================================================

def receive_shipment(db: Session, shipment_id: int):
    """Mark shipment as received and start box entry process."""
    from database.models import Shipment
    from datetime import datetime, timezone

    shipment = get_shipment(db, shipment_id)
    shipment.reception_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(shipment)
    return shipment


def add_box_entry(db: Session, box_id: int, entry_data):
    """Record box entry details."""
    from database.models import ShipmentBox, BoxEntryLog

    box = db.query(ShipmentBox).filter(ShipmentBox.id == box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail="Box not found")

    # Update box with entry data
    if entry_data.receiver_name:
        box.receiver_name = entry_data.receiver_name
    if entry_data.receiver_phone:
        box.receiver_phone = entry_data.receiver_phone
    if entry_data.location_id:
        box.location_id = entry_data.location_id
        box.delivery_type = "pickup"
    if entry_data.delivery_charge:
        box.delivery_charge = entry_data.delivery_charge
    if entry_data.delivery_status:
        box.delivery_status = entry_data.delivery_status

    box.payment_status = entry_data.payment_status or "pending"

    # Create entry log
    log_entry = BoxEntryLog(
        shipment_box_id=box_id,
        entry_type="initial_entry",
        new_value=f"receiver={entry_data.receiver_name}, location={entry_data.location_id}, type={entry_data.delivery_type}",
    )

    db.add(log_entry)
    db.commit()
    db.refresh(box)

    return box


def update_box_delivery_status(db: Session, box_id: int, new_status: str):
    """Update box delivery status and log change."""
    from database.models import ShipmentBox, BoxEntryLog

    box = db.query(ShipmentBox).filter(ShipmentBox.id == box_id).first()
    if not box:
        raise HTTPException(status_code=404, detail="Box not found")

    old_status = box.delivery_status

    # Validate status
    valid_statuses = ["pending", "in-transit", "delivered", "missing", "damaged", "lost", "collected"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    box.delivery_status = new_status

    # Create log entry
    log_entry = BoxEntryLog(
        shipment_box_id=box_id,
        entry_type="status_update",
        old_value=old_status,
        new_value=new_status,
    )

    db.add(log_entry)
    db.commit()
    db.refresh(box)

    # Update shipment totals
    update_shipment_box_totals(db, box.shipment_id)

    return box


def get_reception_status(db: Session, shipment_id: int):
    """Get shipment reception progress."""
    from database.models import Shipment, ShipmentBox

    shipment = get_shipment(db, shipment_id)

    total_boxes = shipment.total_boxes
    boxes_with_entry = db.query(ShipmentBox).filter(
        ShipmentBox.shipment_id == shipment_id,
        ShipmentBox.receiver_name.isnot(None)
    ).count()

    percentage = (boxes_with_entry / total_boxes * 100) if total_boxes > 0 else 0

    return {
        "shipment_id": shipment_id,
        "total_boxes": total_boxes,
        "boxes_entered": boxes_with_entry,
        "boxes_pending": total_boxes - boxes_with_entry,
        "status_percentage": round(percentage, 2),
        "is_reception_complete": shipment.is_reception_complete,
    }


def update_shipment_box_totals(db: Session, shipment_id: int):
    """Update shipment totals based on boxes."""
    from database.models import Shipment, ShipmentBox

    shipment = get_shipment(db, shipment_id)
    boxes = db.query(ShipmentBox).filter(ShipmentBox.shipment_id == shipment_id).all()

    # Count by delivery status
    shipment.total_prebooking_boxes = sum(1 for b in boxes if b.delivery_type == "prebooking")
    shipment.total_pickup_boxes = sum(1 for b in boxes if b.delivery_type == "pickup")
    shipment.total_pending_boxes = sum(1 for b in boxes if b.delivery_status == "pending")
    shipment.total_in_transit_boxes = sum(1 for b in boxes if b.delivery_status == "in-transit")
    shipment.total_delivered_boxes = sum(1 for b in boxes if b.delivery_status == "delivered")
    shipment.total_missing_boxes = sum(1 for b in boxes if b.delivery_status == "missing")
    shipment.total_damaged_boxes = sum(1 for b in boxes if b.delivery_status in ["damaged", "lost"])

    # Calculate payment totals
    from database.models import PaymentRecord
    payments = db.query(PaymentRecord).join(
        ShipmentBox, ShipmentBox.id == PaymentRecord.shipment_box_id
    ).filter(ShipmentBox.shipment_id == shipment_id).all()

    shipment.total_pending_payment = sum(p.amount for p in payments if p.payment_status == "pending")
    shipment.total_collected_payment = sum(p.amount for p in payments if p.payment_status == "paid")
    shipment.total_partial_payment = sum(p.amount for p in payments if p.payment_status == "partial")

    total_payment = shipment.total_pending_payment + shipment.total_collected_payment + shipment.total_partial_payment
    if total_payment > 0:
        shipment.collection_percentage = (shipment.total_collected_payment / total_payment * 100)

    db.commit()


# ============================================================================
# Reporting and Analytics
# ============================================================================

def get_shipment_status_report(db: Session, shipment_id: int):
    """Generate detailed status report for a shipment."""
    from database.models import ShipmentBox

    shipment = get_shipment(db, shipment_id)
    boxes = db.query(ShipmentBox).filter(ShipmentBox.shipment_id == shipment_id).all()

    status_breakdown = {}
    for status in ["pending", "in-transit", "delivered", "missing", "damaged", "lost", "collected"]:
        status_breakdown[status] = sum(1 for b in boxes if b.delivery_status == status)

    return {
        "shipment_ref": shipment.shipment_ref,
        "total_boxes": shipment.total_boxes,
        "status_breakdown": status_breakdown,
        "completion_percentage": ((shipment.total_delivered_boxes + shipment.total_pickup_boxes) / shipment.total_boxes * 100) if shipment.total_boxes > 0 else 0,
        "ready_for_report": shipment.is_reception_complete == 1,
    }


def get_pending_payments_across_shipments(db: Session):
    """Get all pending payments across all shipments."""
    from database.models import PaymentRecord, ShipmentBox, Shipment

    records = db.query(PaymentRecord).join(
        ShipmentBox, ShipmentBox.id == PaymentRecord.shipment_box_id
    ).join(
        Shipment, Shipment.id == ShipmentBox.shipment_id
    ).filter(PaymentRecord.payment_status == "pending").all()

    return {
        "pending_records": len(records),
        "total_pending_amount": sum(r.amount for r in records),
        "details": [
            {
                "payment_id": r.id,
                "shipment_ref": r.shipment_box.shipment.shipment_ref,
                "box_number": r.shipment_box.box_number,
                "amount": float(r.amount),
                "created_at": r.created_at,
            }
            for r in records
        ]
    }
