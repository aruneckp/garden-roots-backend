from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey,
    Date, Float, UniqueConstraint,
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
