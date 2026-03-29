# Garden Roots — Data Model Reference

## Summary

18 tables total across 2 phases:
- **Base schema** (01_create_tables.sql): 17 tables
- **Migrations** (05–08): 1 new table (USERS) + 6 columns added to ORDERS

---

## Table Creation Order (FK Dependency)

```
Phase 1 — Independent tables (no FK parents)
  1.  PRODUCTS
  2.  LOCATIONS
  3.  ADMIN_USERS
  4.  SPOC_CONTACTS
  5.  PICKUP_LOCATIONS

Phase 2 — First-level dependents
  6.  PRODUCT_VARIANTS         FK → products
  7.  SHIPMENTS                FK → products, spoc_contacts
  8.  ORDERS                   (base: no FK yet; FKs added in migrations 05/06/08)

Phase 3 — Second-level dependents
  9.  PRICING                  FK → product_variants
  10. STOCK_INVENTORY          FK → product_variants
  11. ORDER_ITEMS              FK → orders, product_variants
  12. SHIPMENT_BOXES           FK → shipments, pickup_locations, product_variants

Phase 4 — Third-level dependents
  13. DELIVERY_LOGS            FK → shipment_boxes, locations, orders
  14. SHIPMENT_SUMMARY         FK → shipments
  15. PREBOOKINGS              FK → shipments, shipment_boxes
  16. PAYMENT_RECORDS          FK → shipment_boxes, prebookings
  17. BOX_ENTRY_LOGS           FK → shipment_boxes, admin_users

Migration 05
  18. USERS                    (new table)
      orders.user_id           FK → users

Migration 06
      orders.delivery_type
      orders.pickup_location_id  FK → pickup_locations
      orders.customer_notes
      pickup_locations.whatsapp_phone

Migration 07
      orders.delivery_feedback

Migration 08
      orders.shipment_id       FK → shipments
```

---

## Drop Order (Reverse of Creation — for 00_drop_all.sql)

```
BOX_ENTRY_LOGS → PAYMENT_RECORDS → PREBOOKINGS → SHIPMENT_SUMMARY
→ DELIVERY_LOGS → SHIPMENT_BOXES → ORDER_ITEMS → SHIPMENTS
→ ORDERS → USERS → STOCK_INVENTORY → PRICING
→ PRODUCT_VARIANTS → PICKUP_LOCATIONS → SPOC_CONTACTS
→ ADMIN_USERS → LOCATIONS → PRODUCTS
```

---

## Table Definitions

### PRODUCTS
Core product catalog.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| name | VARCHAR2(100) NOT NULL | UNIQUE |
| description | VARCHAR2(500) | |
| origin | VARCHAR2(150) | |
| season_start | VARCHAR2(10) | |
| season_end | VARCHAR2(10) | |
| tag | VARCHAR2(50) | |
| created_at | TIMESTAMP WITH TIME ZONE | |
| updated_at | TIMESTAMP WITH TIME ZONE | |

---

### LOCATIONS
Delivery drop-off locations (admin-managed).

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| location_name | VARCHAR2(150) NOT NULL | |
| address | VARCHAR2(300) NOT NULL | |
| latitude | FLOAT | |
| longitude | FLOAT | |
| operating_hours | VARCHAR2(100) | |
| created_at | TIMESTAMP WITH TIME ZONE | |

---

### ADMIN_USERS
Backend admin login accounts.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| username | VARCHAR2(100) NOT NULL | UNIQUE |
| password_hash | VARCHAR2(255) NOT NULL | bcrypt |
| full_name | VARCHAR2(150) | |
| email | VARCHAR2(150) | |
| role | VARCHAR2(50) | DEFAULT 'admin' |
| is_active | NUMBER(1) | CHECK (0\|1), DEFAULT 1 |
| created_at | TIMESTAMP WITH TIME ZONE | |
| updated_at | TIMESTAMP WITH TIME ZONE | |

---

### SPOC_CONTACTS
Supplier single point of contact.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| name | VARCHAR2(150) NOT NULL | |
| phone | VARCHAR2(20) NOT NULL | |
| email | VARCHAR2(150) | |
| location | VARCHAR2(200) | |
| created_at | TIMESTAMP WITH TIME ZONE | |

---

### PICKUP_LOCATIONS
Customer self-pickup points (warehouse / retail).

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| name | VARCHAR2(150) NOT NULL | |
| address | VARCHAR2(500) NOT NULL | |
| phone | VARCHAR2(20) | |
| email | VARCHAR2(150) | |
| manager_name | VARCHAR2(150) | |
| location_type | VARCHAR2(50) | DEFAULT 'retail' |
| capacity | NUMBER(10) | |
| current_boxes | NUMBER(10) | DEFAULT 0, CHECK >= 0 |
| is_active | NUMBER(1) | CHECK (0\|1), DEFAULT 1 |
| notes | VARCHAR2(1000) | |
| whatsapp_phone | VARCHAR2(20) | Added in migration 06 |
| created_at | TIMESTAMP WITH TIME ZONE | |
| updated_at | TIMESTAMP WITH TIME ZONE | |

---

### USERS
Customer accounts via Google OAuth. Added in migration 05.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| google_id | VARCHAR2(100) NOT NULL | UNIQUE |
| email | VARCHAR2(150) NOT NULL | UNIQUE |
| name | VARCHAR2(150) | |
| picture | VARCHAR2(500) | |
| phone | VARCHAR2(20) | |
| whatsapp_phone | VARCHAR2(20) | |
| created_at | TIMESTAMP WITH TIME ZONE | |
| updated_at | TIMESTAMP WITH TIME ZONE | |

**Indexes:** idx_users_google_id, idx_users_email

---

### PRODUCT_VARIANTS
Size/unit variants per product (e.g., "1kg box", "5kg bag").

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| product_id | NUMBER(10) NOT NULL | FK → products ON DELETE CASCADE |
| size_name | VARCHAR2(100) NOT NULL | UNIQUE with product_id |
| unit | VARCHAR2(50) NOT NULL | |
| created_at | TIMESTAMP WITH TIME ZONE | |

---

### PRICING
Price records per variant with optional validity window.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| product_variant_id | NUMBER(10) NOT NULL | FK → product_variants ON DELETE CASCADE |
| base_price | NUMBER(10,2) NOT NULL | |
| currency | VARCHAR2(10) | DEFAULT 'USD' |
| valid_from | DATE | |
| valid_to | DATE | CHECK valid_to >= valid_from |
| created_at | TIMESTAMP WITH TIME ZONE | |
| updated_at | TIMESTAMP WITH TIME ZONE | |

---

### STOCK_INVENTORY
Current stock level per variant (one row per variant).

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| product_variant_id | NUMBER(10) NOT NULL | FK → product_variants ON DELETE CASCADE, UNIQUE |
| quantity_available | NUMBER(10) | DEFAULT 0, CHECK >= 0 |
| reserved_quantity | NUMBER(10) | DEFAULT 0, CHECK >= 0 |
| warehouse_location | VARCHAR2(200) | |
| last_updated | TIMESTAMP WITH TIME ZONE | |

---

### ORDERS
Customer purchase orders.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| order_ref | VARCHAR2(50) NOT NULL | UNIQUE |
| customer_name | VARCHAR2(150) NOT NULL | |
| customer_email | VARCHAR2(150) | |
| customer_phone | VARCHAR2(20) | |
| subtotal | NUMBER(10,2) NOT NULL | CHECK >= 0 |
| delivery_fee | NUMBER(10,2) | DEFAULT 0, CHECK >= 0 |
| total_price | NUMBER(10,2) NOT NULL | CHECK >= 0 |
| payment_method | VARCHAR2(50) | |
| payment_status | VARCHAR2(50) | DEFAULT 'pending' |
| payment_intent_id | VARCHAR2(300) | |
| order_status | VARCHAR2(50) | DEFAULT 'pending' |
| delivery_address | VARCHAR2(500) | |
| user_id | NUMBER | FK → users ON DELETE SET NULL (migration 05) |
| delivery_type | VARCHAR2(20) | CHECK ('delivery'\|'pickup'), DEFAULT 'delivery' (migration 06) |
| pickup_location_id | NUMBER | FK → pickup_locations ON DELETE SET NULL (migration 06) |
| customer_notes | VARCHAR2(1000) | (migration 06) |
| delivery_feedback | VARCHAR2(2000) | (migration 07) |
| shipment_id | NUMBER | FK → shipments ON DELETE SET NULL (migration 08) |
| created_at | TIMESTAMP WITH TIME ZONE | |
| updated_at | TIMESTAMP WITH TIME ZONE | |

**Indexes:** payment_status, order_status, user_id, delivery_type, pickup_location_id, shipment_id

---

### SHIPMENTS
Incoming bulk product shipments from suppliers.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| shipment_ref | VARCHAR2(50) NOT NULL | UNIQUE |
| product_id | NUMBER(10) NOT NULL | FK → products |
| total_boxes | NUMBER(10) NOT NULL | CHECK >= 0 |
| expected_value | NUMBER(15,2) | |
| status | VARCHAR2(50) | DEFAULT 'pending' |
| spoc_contact_id | NUMBER(10) | FK → spoc_contacts |
| received_date | TIMESTAMP WITH TIME ZONE | |
| completion_date | TIMESTAMP WITH TIME ZONE | |
| notes | VARCHAR2(1000) | |
| reception_date | TIMESTAMP WITH TIME ZONE | |
| expected_reception_date | TIMESTAMP WITH TIME ZONE | |
| expected_delivery_date | TIMESTAMP WITH TIME ZONE | |
| is_reception_complete | NUMBER(1) | CHECK (0\|1), DEFAULT 0 |
| total_prebooking_boxes | NUMBER(10) | DEFAULT 0 (aggregate cache) |
| total_pickup_boxes | NUMBER(10) | DEFAULT 0 (aggregate cache) |
| total_pending_boxes | NUMBER(10) | DEFAULT 0 (aggregate cache) |
| total_in_transit_boxes | NUMBER(10) | DEFAULT 0 (aggregate cache) |
| total_delivered_boxes | NUMBER(10) | DEFAULT 0 (aggregate cache) |
| total_missing_boxes | NUMBER(10) | DEFAULT 0 (aggregate cache) |
| total_damaged_boxes | NUMBER(10) | DEFAULT 0 (aggregate cache) |
| total_pending_payment | NUMBER(15,2) | DEFAULT 0 (aggregate cache) |
| total_collected_payment | NUMBER(15,2) | DEFAULT 0 (aggregate cache) |
| total_partial_payment | NUMBER(15,2) | DEFAULT 0 (aggregate cache) |
| collection_percentage | NUMBER(5,2) | DEFAULT 0 |
| created_at | TIMESTAMP WITH TIME ZONE | |
| updated_at | TIMESTAMP WITH TIME ZONE | |

---

### ORDER_ITEMS
Line items within a customer order.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| order_id | NUMBER(10) NOT NULL | FK → orders ON DELETE CASCADE |
| product_variant_id | NUMBER(10) NOT NULL | FK → product_variants |
| quantity | NUMBER(10) NOT NULL | CHECK > 0 |
| unit_price | NUMBER(10,2) NOT NULL | CHECK >= 0 |
| subtotal | NUMBER(10,2) NOT NULL | CHECK >= 0 |
| created_at | TIMESTAMP WITH TIME ZONE | |

---

### SHIPMENT_BOXES
Individual boxes within a shipment.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| shipment_id | NUMBER(10) NOT NULL | FK → shipments ON DELETE CASCADE |
| box_number | VARCHAR2(100) NOT NULL | UNIQUE with shipment_id |
| quantity_boxes | NUMBER(10) | DEFAULT 1, CHECK >= 1 |
| box_status | VARCHAR2(50) | DEFAULT 'in-stock' |
| delivery_type | VARCHAR2(50) | DEFAULT 'pending' |
| delivery_charge | NUMBER(10,2) | DEFAULT 0, CHECK >= 0 |
| receiver_name | VARCHAR2(150) | |
| receiver_phone | VARCHAR2(20) | |
| location_id | NUMBER(10) | FK → pickup_locations |
| delivery_status | VARCHAR2(50) | DEFAULT 'pending' |
| payment_status | VARCHAR2(50) | DEFAULT 'pending' |
| product_variant_id | NUMBER(10) | FK → product_variants |
| variety_size | VARCHAR2(50) | |
| quantity_per_variety | NUMBER(10) | DEFAULT 1, CHECK >= 1 |
| created_at | TIMESTAMP WITH TIME ZONE | |
| updated_at | TIMESTAMP WITH TIME ZONE | |

**Indexes:** box_status, delivery_status, payment_status

---

### DELIVERY_LOGS
Delivery attempt records per shipment box.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| shipment_box_id | NUMBER(10) NOT NULL | FK → shipment_boxes ON DELETE CASCADE |
| location_id | NUMBER(10) | FK → locations |
| order_id | NUMBER(10) | FK → orders |
| delivery_address | VARCHAR2(500) | |
| delivery_date | TIMESTAMP WITH TIME ZONE | |
| delivery_notes | VARCHAR2(500) | |
| receiver_name | VARCHAR2(150) | |
| receiver_phone | VARCHAR2(20) | |
| is_direct_delivery | NUMBER(1) | CHECK (0\|1), DEFAULT 0 |
| created_at | TIMESTAMP WITH TIME ZONE | |

---

### SHIPMENT_SUMMARY
Aggregated statistics snapshot per shipment (one row per shipment).

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| shipment_id | NUMBER(10) NOT NULL | FK → shipments ON DELETE CASCADE, UNIQUE |
| total_boxes_received | NUMBER(10) NOT NULL | CHECK >= 0 |
| boxes_delivered_direct | NUMBER(10) | DEFAULT 0, CHECK >= 0 |
| boxes_collected_self | NUMBER(10) | DEFAULT 0, CHECK >= 0 |
| boxes_damaged | NUMBER(10) | DEFAULT 0, CHECK >= 0 |
| total_delivery_revenue | NUMBER(15,2) | DEFAULT 0 |
| delivery_locations_count | NUMBER(10) | DEFAULT 0 |
| summary_json | VARCHAR2(4000) | flexible JSON blob |
| generated_at | TIMESTAMP WITH TIME ZONE | |

---

### PREBOOKINGS
Pre-scheduled customer deliveries against a shipment box.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| shipment_id | NUMBER(10) NOT NULL | FK → shipments ON DELETE CASCADE |
| shipment_box_id | NUMBER(10) NOT NULL | FK → shipment_boxes ON DELETE CASCADE |
| customer_name | VARCHAR2(150) NOT NULL | |
| customer_phone | VARCHAR2(20) NOT NULL | |
| customer_email | VARCHAR2(150) | |
| delivery_address | VARCHAR2(500) NOT NULL | |
| booking_date | TIMESTAMP WITH TIME ZONE | DEFAULT SYSTIMESTAMP |
| scheduled_delivery_date | TIMESTAMP WITH TIME ZONE | |
| status | VARCHAR2(50) | DEFAULT 'booked' |
| created_at | TIMESTAMP WITH TIME ZONE | |
| updated_at | TIMESTAMP WITH TIME ZONE | |

**Indexes:** shipment_id, shipment_box_id, status

---

### PAYMENT_RECORDS
Payment records per shipment box (linked optionally to a prebooking).

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| shipment_box_id | NUMBER(10) NOT NULL | FK → shipment_boxes ON DELETE CASCADE |
| prebooking_id | NUMBER(10) | FK → prebookings ON DELETE SET NULL |
| description | VARCHAR2(500) | |
| amount | NUMBER(10,2) NOT NULL | CHECK >= 0 |
| payment_status | VARCHAR2(50) | DEFAULT 'pending' |
| payment_date | TIMESTAMP WITH TIME ZONE | |
| payment_method | VARCHAR2(50) | |
| transaction_ref | VARCHAR2(150) | |
| notes | VARCHAR2(500) | |
| created_at | TIMESTAMP WITH TIME ZONE | |
| updated_at | TIMESTAMP WITH TIME ZONE | |

**Indexes:** shipment_box_id, payment_status

---

### BOX_ENTRY_LOGS
Audit trail for all status changes on shipment boxes.

| Column | Type | Notes |
|--------|------|-------|
| id | NUMBER IDENTITY PK | |
| shipment_box_id | NUMBER(10) NOT NULL | FK → shipment_boxes ON DELETE CASCADE |
| entry_type | VARCHAR2(50) | change category |
| old_value | VARCHAR2(500) | |
| new_value | VARCHAR2(500) | |
| changed_by | NUMBER(10) | FK → admin_users ON DELETE SET NULL |
| created_at | TIMESTAMP WITH TIME ZONE | |

**Indexes:** shipment_box_id, entry_type

---

## FK Relationship Map

```
PRODUCTS ─────────────────────┬─► PRODUCT_VARIANTS ──┬─► PRICING
                               │                      ├─► STOCK_INVENTORY
                               │                      ├─► ORDER_ITEMS
                               │                      └─► SHIPMENT_BOXES
                               └─► SHIPMENTS ──────────┬─► SHIPMENT_BOXES ──┬─► DELIVERY_LOGS
                                                        │                    ├─► PAYMENT_RECORDS
                                                        │                    └─► BOX_ENTRY_LOGS
                                                        ├─► SHIPMENT_SUMMARY
                                                        └─► PREBOOKINGS ──────► PAYMENT_RECORDS

SPOC_CONTACTS ───────────────────► SHIPMENTS

ADMIN_USERS ─────────────────────► BOX_ENTRY_LOGS

PICKUP_LOCATIONS ────────────────┬─► SHIPMENT_BOXES
                                  └─► ORDERS (migration 06)

LOCATIONS ───────────────────────► DELIVERY_LOGS

USERS (migration 05) ────────────► ORDERS

ORDERS ──────────────────────────► ORDER_ITEMS
                                    DELIVERY_LOGS
                                    (shipment_id → SHIPMENTS, migration 08)
```

---

## Design Conventions

| Convention | Detail |
|------------|--------|
| Primary keys | `GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1)` |
| Timestamps | `TIMESTAMP WITH TIME ZONE` — all UTC-aware |
| Boolean flags | `NUMBER(1)` with `CHECK (col IN (0, 1))` |
| Money fields | `NUMBER(10,2)` for order-level; `NUMBER(15,2)` for shipment-level |
| Cascade on delete | Product → variants → pricing/stock/order_items; shipment → boxes → logs/payments |
| SET NULL on delete | user_id, pickup_location_id, shipment_id on orders; prebooking_id on payment_records |
| Idempotent seeds | `MERGE INTO` used in 03_seed_data.sql |
| Soft boolean (is_active) | Used on admin_users and pickup_locations |
