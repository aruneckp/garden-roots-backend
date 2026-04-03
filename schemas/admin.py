from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date


# ============================================================================
# Auth Schemas
# ============================================================================

class AdminLoginIn(BaseModel):
    username: str
    password: str


class AdminTokenOut(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    role: str


# ============================================================================
# SPOC Contact Schemas
# ============================================================================

class SPOCContactIn(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    location: Optional[str] = None


class SPOCContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    email: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime


# ============================================================================
# Shipment Variety Schemas
# ============================================================================

class ShipmentVarietyIn(BaseModel):
    product_id: int
    box_count: int = 1
    box_weight: Optional[float] = None    # weight per box in kg
    price_per_kg: Optional[float] = None  # price per kg for this variety


class ShipmentVarietyOut(BaseModel):
    product_id: Optional[int] = None
    variety_name: str
    box_count: int
    box_weight: Optional[float] = None
    price_per_kg: Optional[float] = None


# ============================================================================
# Shipment Box Schemas
# ============================================================================

class ShipmentBoxIn(BaseModel):
    box_number: str
    quantity_boxes: int = 1
    delivery_type: str = "pending"  # pending, direct-delivery, self-collection
    delivery_charge: float = 0.0


class ShipmentBoxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    box_number: str
    quantity_boxes: int
    box_status: str
    delivery_type: str
    delivery_charge: float
    product_variant_id: Optional[int] = None
    variety_size: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ShipmentBoxUpdate(BaseModel):
    box_status: Optional[str] = None
    delivery_type: Optional[str] = None
    delivery_charge: Optional[float] = None


# ============================================================================
# Shipment Schemas
# ============================================================================

class ShipmentIn(BaseModel):
    product_id: Optional[int] = None  # derived from first variety if not provided
    total_boxes: int = Field(default=1, ge=1)
    expected_value: Optional[float] = None
    spoc_contact_id: Optional[int] = None
    notes: Optional[str] = None
    varieties: List[ShipmentVarietyIn] = []


class ShipmentUpdate(BaseModel):
    status: Optional[str] = None
    spoc_contact_id: Optional[int] = None
    notes: Optional[str] = None


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_ref: str
    product_id: int
    total_boxes: int
    expected_value: Optional[float] = None
    status: str
    spoc_contact_id: Optional[int] = None
    received_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    notes: Optional[str] = None
    variety_names: List[str] = []
    created_at: datetime
    updated_at: datetime


class ShipmentDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_ref: str
    product_id: int
    total_boxes: int
    expected_value: Optional[float] = None
    status: str
    spoc_contact: Optional[SPOCContactOut] = None
    received_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    notes: Optional[str] = None
    boxes: List[ShipmentBoxOut] = []
    varieties: List[ShipmentVarietyOut] = []
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Delivery Log Schemas
# ============================================================================

class DeliveryLogIn(BaseModel):
    location_id: Optional[int] = None
    order_id: Optional[int] = None
    delivery_address: Optional[str] = None
    delivery_notes: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    is_direct_delivery: bool = False


class DeliveryLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_box_id: int
    location_id: Optional[int] = None
    order_id: Optional[int] = None
    delivery_address: Optional[str] = None
    delivery_date: Optional[datetime] = None
    delivery_notes: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    is_direct_delivery: bool
    created_at: datetime


# ============================================================================
# Shipment Summary Schemas
# ============================================================================

class ShipmentSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    total_boxes_received: int
    boxes_delivered_direct: int
    boxes_collected_self: int
    boxes_damaged: int
    total_delivery_revenue: float
    delivery_locations_count: int
    summary_json: Optional[str] = None
    generated_at: datetime


class ShipmentConsolidatedSummary(BaseModel):
    shipment_ref: str
    total_boxes: int
    boxes_delivered_direct: int
    boxes_collected_self: int
    boxes_damaged: int
    total_delivery_revenue: float
    delivery_locations: List[dict]
    spoc_contact: Optional[SPOCContactOut] = None
    summary_by_location: List[dict]
    varieties: List[dict] = []


# ============================================================================
# Pickup Location Schemas
# ============================================================================

class PickupLocationIn(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None
    location_type: str = "retail"  # retail, warehouse, franchise, store
    capacity: int = 100
    notes: Optional[str] = None


class PickupLocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None
    location_type: str
    capacity: int
    current_boxes: int
    is_active: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PickupLocationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None
    capacity: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[int] = None


class PickupLocationOccupancy(BaseModel):
    location_id: int
    location_name: str
    capacity: int
    boxes_stored: int
    occupancy_percentage: float
    pending_boxes: int
    in_transit_boxes: int


# ============================================================================
# Prebooking Schemas
# ============================================================================

class PrebookingIn(BaseModel):
    shipment_id: int
    shipment_box_id: int
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    delivery_address: str
    scheduled_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None


class PrebookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    shipment_box_id: int
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    delivery_address: str
    booking_date: datetime
    scheduled_delivery_date: Optional[datetime] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PrebookingStatusUpdate(BaseModel):
    status: str  # booked, confirmed, in-transit, delivered, cancelled
    notes: Optional[str] = None


# ============================================================================
# Payment Record Schemas
# ============================================================================

class PaymentRecordIn(BaseModel):
    shipment_box_id: int
    prebooking_id: Optional[int] = None
    description: Optional[str] = None
    amount: float
    payment_method: Optional[str] = None  # cash, online, check, credit, upi
    transaction_ref: Optional[str] = None
    notes: Optional[str] = None


class PaymentRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_box_id: int
    prebooking_id: Optional[int] = None
    description: Optional[str] = None
    amount: float
    payment_status: str
    payment_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    transaction_ref: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaymentRecordUpdate(BaseModel):
    payment_status: str  # pending, paid, cancelled
    payment_date: Optional[datetime] = None
    payment_method: Optional[str] = None
    transaction_ref: Optional[str] = None
    notes: Optional[str] = None


class PaymentSummary(BaseModel):
    total_payment_records: int
    pending_count: int
    paid_count: int
    pending_amount: float
    paid_amount: float
    total_amount: float
    collection_percentage: float


# ============================================================================
# Box Entry Log Schemas
# ============================================================================

class BoxEntryLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_box_id: int
    entry_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[int] = None
    created_at: datetime


# ============================================================================
# Enhanced Box Schemas (with location and prebooking info)
# ============================================================================

class ShipmentBoxEnhancedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    box_number: str
    quantity_boxes: int
    box_status: str
    delivery_type: str
    delivery_charge: float
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    location_id: Optional[int] = None
    prebooking_id: Optional[int] = None
    delivery_status: str
    payment_status: str
    created_at: datetime
    updated_at: datetime


class ShipmentBoxEntryIn(BaseModel):
    """Input schema for entering/updating box details"""
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    delivery_type: str  # "prebooking" or "pickup"
    location_id: Optional[int] = None  # for pickup type
    prebooking_id: Optional[int] = None  # for prebooking type
    delivery_charge: float = 0.0
    payment_status: Optional[str] = None
    delivery_status: Optional[str] = None


# ============================================================================
# Delivery Boy Schemas
# ============================================================================

class DeliveryBoyIn(BaseModel):
    username:  str
    password:  str
    full_name: Optional[str] = None
    phone:     Optional[str] = None


class DeliveryBoyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:        int
    username:  str
    full_name: Optional[str] = None
    phone:     Optional[str] = None
    is_active: int
    created_at: datetime


class AssignDeliveryIn(BaseModel):
    order_ids:      List[int]
    delivery_date:  date   # used to build code: username_yyyymmdd


class DeliveryBoyLoginIn(BaseModel):
    username: str
    password: str


class DeliveryBoyTokenOut(BaseModel):
    access_token:    str
    token_type:      str = "bearer"
    delivery_boy_id: int
    username:        str
    full_name:       Optional[str] = None


# ============================================================================
# Order Management Schemas
# ============================================================================

class OrderBulkStatusIn(BaseModel):
    order_ids:  List[int]
    new_status: str          # confirmed, shipped, delivered, cancelled, pending
    note:       Optional[str] = None


class OrderShipmentUpdate(BaseModel):
    shipment_id: Optional[int] = None   # None to clear the link


class OrderBulkShipmentIn(BaseModel):
    shipment_id: int                         # shipment to assign
    order_ids: Optional[List[int]] = None    # specific orders; None = all with null shipment_id
    only_null: bool = True                   # when order_ids is None, skip orders already linked

