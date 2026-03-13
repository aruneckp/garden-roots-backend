from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey,
    Date, Float, UniqueConstraint, Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.connection import Base


def _now():
    """timezone-aware UTC timestamp (replaces deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(500))
    origin      = Column(String(150))
    season_start= Column(String(10))
    season_end  = Column(String(10))
    tag         = Column(String(50))
    created_at  = Column(DateTime(timezone=True), default=_now)
    updated_at  = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("product_id", "size_name"),)

    id         = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    size_name  = Column(String(100), nullable=False)
    unit       = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    product    = relationship("Product", back_populates="variants")
    pricing    = relationship("Pricing", back_populates="product_variant", cascade="all, delete-orphan")
    stock      = relationship("StockInventory", back_populates="product_variant", uselist=False, cascade="all, delete-orphan")
    order_items= relationship("OrderItem", back_populates="product_variant")


class Pricing(Base):
    __tablename__ = "pricing"

    id                 = Column(Integer, primary_key=True, index=True)
    product_variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False, index=True)
    base_price         = Column(Numeric(10, 2), nullable=False)
    currency           = Column(String(10), default="USD")
    valid_from         = Column(Date)
    valid_to           = Column(Date)
    created_at         = Column(DateTime(timezone=True), default=_now)
    updated_at         = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    product_variant = relationship("ProductVariant", back_populates="pricing")


class StockInventory(Base):
    __tablename__ = "stock_inventory"
    __table_args__ = (UniqueConstraint("product_variant_id"),)

    id                 = Column(Integer, primary_key=True, index=True)
    product_variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False, index=True)
    quantity_available = Column(Integer, default=0)
    reserved_quantity  = Column(Integer, default=0)
    warehouse_location = Column(String(200))
    last_updated       = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    product_variant = relationship("ProductVariant", back_populates="stock")


class Location(Base):
    __tablename__ = "locations"

    id              = Column(Integer, primary_key=True, index=True)
    location_name   = Column(String(150), nullable=False)
    address         = Column(String(300), nullable=False)
    latitude        = Column(Float)
    longitude       = Column(Float)
    operating_hours = Column(String(100))
    created_at      = Column(DateTime(timezone=True), default=_now)


class Order(Base):
    __tablename__ = "orders"

    id                = Column(Integer, primary_key=True, index=True)
    order_ref         = Column(String(50), unique=True, nullable=False, index=True)
    customer_name     = Column(String(150), nullable=False)
    customer_email    = Column(String(150))
    customer_phone    = Column(String(20))
    subtotal          = Column(Numeric(10, 2), nullable=False)
    delivery_fee      = Column(Numeric(10, 2), default=0)
    total_price       = Column(Numeric(10, 2), nullable=False)
    payment_method    = Column(String(50))
    payment_status    = Column(String(50), default="pending", index=True)
    payment_intent_id = Column(String(300))
    order_status      = Column(String(50), default="pending", index=True)
    delivery_address  = Column(String(500))
    created_at        = Column(DateTime(timezone=True), default=_now)
    updated_at        = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id                 = Column(Integer, primary_key=True, index=True)
    order_id           = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False, index=True)
    quantity           = Column(Integer, nullable=False)
    unit_price         = Column(Numeric(10, 2), nullable=False)
    subtotal           = Column(Numeric(10, 2), nullable=False)
    created_at         = Column(DateTime(timezone=True), default=_now)

    order           = relationship("Order", back_populates="order_items")
    product_variant = relationship("ProductVariant", back_populates="order_items")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id          = Column(Integer, primary_key=True, index=True)
    username    = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name   = Column(String(150))
    email       = Column(String(150))
    role        = Column(String(50), default="admin")
    is_active   = Column(Integer, default=1)
    created_at  = Column(DateTime(timezone=True), default=_now)
    updated_at  = Column(DateTime(timezone=True), default=_now, onupdate=_now)


class SPOCContact(Base):
    __tablename__ = "spoc_contacts"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(150), nullable=False)
    phone       = Column(String(20), nullable=False)
    email       = Column(String(150))
    location    = Column(String(200))
    created_at  = Column(DateTime(timezone=True), default=_now)

    shipments = relationship("Shipment", back_populates="spoc_contact")


class Shipment(Base):
    __tablename__ = "shipments"

    id                      = Column(Integer, primary_key=True, index=True)
    shipment_ref            = Column(String(50), unique=True, nullable=False, index=True)
    product_id              = Column(Integer, ForeignKey("products.id"), nullable=False)
    total_boxes             = Column(Integer, nullable=False)
    expected_value          = Column(Numeric(15, 2))
    status                  = Column(String(50), default="pending", index=True)
    spoc_contact_id         = Column(Integer, ForeignKey("spoc_contacts.id"))
    received_date           = Column(DateTime(timezone=True))
    completion_date         = Column(DateTime(timezone=True))
    notes                   = Column(String(1000))
    # New columns for enhanced tracking
    reception_date          = Column(DateTime(timezone=True))
    expected_reception_date = Column(DateTime(timezone=True))
    expected_delivery_date  = Column(DateTime(timezone=True))
    is_reception_complete   = Column(Integer, default=0)
    total_prebooking_boxes  = Column(Integer, default=0)
    total_pickup_boxes      = Column(Integer, default=0)
    total_pending_boxes     = Column(Integer, default=0)
    total_in_transit_boxes  = Column(Integer, default=0)
    total_delivered_boxes   = Column(Integer, default=0)
    total_missing_boxes     = Column(Integer, default=0)
    total_damaged_boxes     = Column(Integer, default=0)
    total_pending_payment   = Column(Numeric(15, 2), default=0)
    total_collected_payment = Column(Numeric(15, 2), default=0)
    total_partial_payment   = Column(Numeric(15, 2), default=0)
    collection_percentage   = Column(Numeric(5, 2), default=0)
    created_at              = Column(DateTime(timezone=True), default=_now)
    updated_at              = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    product         = relationship("Product")
    spoc_contact    = relationship("SPOCContact", back_populates="shipments")
    boxes           = relationship("ShipmentBox", back_populates="shipment", cascade="all, delete-orphan")
    summary         = relationship("ShipmentSummary", back_populates="shipment", uselist=False, cascade="all, delete-orphan")
    prebookings     = relationship("Prebooking", back_populates="shipment", cascade="all, delete-orphan")


class ShipmentBox(Base):
    __tablename__ = "shipment_boxes"
    __table_args__ = (UniqueConstraint("shipment_id", "box_number"),)

    id                  = Column(Integer, primary_key=True, index=True)
    shipment_id         = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    box_number          = Column(String(100), nullable=False)
    quantity_boxes      = Column(Integer, default=1)
    box_status          = Column(String(50), default="in-stock", index=True)
    delivery_type       = Column(String(50), default="pending")
    delivery_charge     = Column(Numeric(10, 2), default=0)
    # New columns for enhanced tracking
    receiver_name       = Column(String(150))
    receiver_phone      = Column(String(20))
    location_id         = Column(Integer, ForeignKey("pickup_locations.id"))
    delivery_status     = Column(String(50), default="pending", index=True)
    payment_status      = Column(String(50), default="pending", index=True)
    # Variety tracking columns
    product_variant_id  = Column(Integer, ForeignKey("product_variants.id"))
    variety_size        = Column(String(50))
    quantity_per_variety = Column(Integer, default=1)
    created_at          = Column(DateTime(timezone=True), default=_now)
    updated_at          = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    shipment        = relationship("Shipment", back_populates="boxes")
    delivery_logs   = relationship("DeliveryLog", back_populates="shipment_box", cascade="all, delete-orphan")
    location        = relationship("PickupLocation", back_populates="boxes")
    product_variant = relationship("ProductVariant")
    prebooking      = relationship("Prebooking", back_populates="box", uselist=False, foreign_keys="Prebooking.shipment_box_id")
    payment_records = relationship("PaymentRecord", back_populates="box", cascade="all, delete-orphan")
    entry_logs      = relationship("BoxEntryLog", back_populates="box", cascade="all, delete-orphan")


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id                  = Column(Integer, primary_key=True, index=True)
    shipment_box_id     = Column(Integer, ForeignKey("shipment_boxes.id"), nullable=False, index=True)
    location_id         = Column(Integer, ForeignKey("locations.id"))
    order_id            = Column(Integer, ForeignKey("orders.id"))
    delivery_address    = Column(String(500))
    delivery_date       = Column(DateTime(timezone=True))
    delivery_notes      = Column(String(500))
    receiver_name       = Column(String(150))
    receiver_phone      = Column(String(20))
    is_direct_delivery  = Column(Integer, default=0)
    created_at          = Column(DateTime(timezone=True), default=_now)

    shipment_box        = relationship("ShipmentBox", back_populates="delivery_logs")
    location            = relationship("Location")
    order               = relationship("Order")


class ShipmentSummary(Base):
    __tablename__ = "shipment_summary"

    id                      = Column(Integer, primary_key=True, index=True)
    shipment_id             = Column(Integer, ForeignKey("shipments.id"), nullable=False, unique=True)
    total_boxes_received    = Column(Integer, nullable=False)
    boxes_delivered_direct  = Column(Integer, default=0)
    boxes_collected_self    = Column(Integer, default=0)
    boxes_damaged           = Column(Integer, default=0)
    total_delivery_revenue  = Column(Numeric(15, 2), default=0)
    delivery_locations_count= Column(Integer, default=0)
    summary_json            = Column(String(4000))
    generated_at            = Column(DateTime(timezone=True), default=_now)

    shipment                = relationship("Shipment", back_populates="summary")


# ============================================================================
# NEW MODELS FOR ENHANCED SHIPMENT MANAGEMENT SYSTEM
# ============================================================================

class PickupLocation(Base):
    """Pickup locations for customer self-collection"""
    __tablename__ = "pickup_locations"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(150), nullable=False, index=True)
    address         = Column(String(500), nullable=False)
    phone           = Column(String(20))
    email           = Column(String(150))
    manager_name    = Column(String(150))
    location_type   = Column(String(50), default="retail")
    capacity        = Column(Integer)
    current_boxes   = Column(Integer, default=0)
    is_active       = Column(Integer, default=1, index=True)
    notes           = Column(String(1000))
    created_at      = Column(DateTime(timezone=True), default=_now)
    updated_at      = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    boxes           = relationship("ShipmentBox", back_populates="location", cascade="all, delete-orphan")


class Prebooking(Base):
    """Pre-booked deliveries with customer details"""
    __tablename__ = "prebookings"

    id                      = Column(Integer, primary_key=True, index=True)
    shipment_id             = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    shipment_box_id         = Column(Integer, ForeignKey("shipment_boxes.id"), nullable=False, index=True)
    customer_name           = Column(String(150), nullable=False)
    customer_phone          = Column(String(20), nullable=False)
    customer_email          = Column(String(150))
    delivery_address        = Column(String(500), nullable=False)
    booking_date            = Column(DateTime(timezone=True), default=_now)
    scheduled_delivery_date = Column(DateTime(timezone=True))
    status                  = Column(String(50), default="booked", index=True)
    created_at              = Column(DateTime(timezone=True), default=_now)
    updated_at              = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    shipment                = relationship("Shipment", back_populates="prebookings")
    box                     = relationship("ShipmentBox", back_populates="prebooking")
    payment_records         = relationship("PaymentRecord", back_populates="prebooking", cascade="all, delete-orphan")


class PaymentRecord(Base):
    """Payment tracking per box or prebooking"""
    __tablename__ = "payment_records"

    id              = Column(Integer, primary_key=True, index=True)
    shipment_box_id = Column(Integer, ForeignKey("shipment_boxes.id"), nullable=False, index=True)
    prebooking_id   = Column(Integer, ForeignKey("prebookings.id"))
    description     = Column(String(500))
    amount          = Column(Numeric(10, 2), nullable=False)
    payment_status  = Column(String(50), default="pending", index=True)
    payment_date    = Column(DateTime(timezone=True))
    payment_method  = Column(String(50))
    transaction_ref = Column(String(150))
    notes           = Column(String(500))
    created_at      = Column(DateTime(timezone=True), default=_now)
    updated_at      = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    box             = relationship("ShipmentBox", back_populates="payment_records")
    prebooking      = relationship("Prebooking", back_populates="payment_records")


class BoxEntryLog(Base):
    """Audit trail for box entry and status changes"""
    __tablename__ = "box_entry_logs"

    id              = Column(Integer, primary_key=True, index=True)
    shipment_box_id = Column(Integer, ForeignKey("shipment_boxes.id"), nullable=False, index=True)
    entry_type      = Column(String(50), index=True)
    old_value       = Column(String(500))
    new_value       = Column(String(500))
    changed_by      = Column(Integer, ForeignKey("admin_users.id"))
    created_at      = Column(DateTime(timezone=True), default=_now)

    box             = relationship("ShipmentBox", back_populates="entry_logs")
    admin_user      = relationship("AdminUser")

