-- ============================================================
-- Garden Roots - Create All Tables
-- Database : Oracle 12c+  (XE / XEPDB1)
-- Encoding : UTF-8
-- Notes    :
--   • Uses GENERATED ALWAYS AS IDENTITY (Oracle 12c+).
--   • All timestamps are TIMESTAMP WITH TIME ZONE (UTC-aware).
--   • NUMBER(1) is used for boolean flags (0 = false, 1 = true).
--   • FK cascade behaviour mirrors the SQLAlchemy model definitions.
--   • Tables are created in strict FK-dependency order.
-- ============================================================

-- Stop immediately on any DDL error
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

PROMPT ----------------------------------------------------------
PROMPT  [01] Creating table: PRODUCTS
PROMPT ----------------------------------------------------------
CREATE TABLE products (
    id           NUMBER        GENERATED ALWAYS AS IDENTITY
                                   (START WITH 1 INCREMENT BY 1) NOT NULL,
    name         VARCHAR2(100)  NOT NULL,
    description  VARCHAR2(500),
    origin       VARCHAR2(150),
    season_start VARCHAR2(10),
    season_end   VARCHAR2(10),
    tag          VARCHAR2(50),
    created_at   TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    updated_at   TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_products          PRIMARY KEY (id),
    CONSTRAINT uq_products_name     UNIQUE      (name)
);

PROMPT ----------------------------------------------------------
PROMPT  [02] Creating table: LOCATIONS
PROMPT ----------------------------------------------------------
CREATE TABLE locations (
    id              NUMBER        GENERATED ALWAYS AS IDENTITY
                                      (START WITH 1 INCREMENT BY 1) NOT NULL,
    location_name   VARCHAR2(150)  NOT NULL,
    address         VARCHAR2(300)  NOT NULL,
    latitude        FLOAT,
    longitude       FLOAT,
    operating_hours VARCHAR2(100),
    created_at      TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_locations PRIMARY KEY (id)
);

PROMPT ----------------------------------------------------------
PROMPT  [03] Creating table: ADMIN_USERS
PROMPT ----------------------------------------------------------
CREATE TABLE admin_users (
    id            NUMBER        GENERATED ALWAYS AS IDENTITY
                                    (START WITH 1 INCREMENT BY 1) NOT NULL,
    username      VARCHAR2(100)  NOT NULL,
    password_hash VARCHAR2(255)  NOT NULL,
    full_name     VARCHAR2(150),
    email         VARCHAR2(150),
    role          VARCHAR2(50)   DEFAULT 'admin',
    is_active     NUMBER(1)      DEFAULT 1,
    created_at    TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    updated_at    TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_admin_users          PRIMARY KEY (id),
    CONSTRAINT uq_admin_users_username UNIQUE      (username),
    CONSTRAINT chk_admin_is_active     CHECK       (is_active IN (0, 1))
);

PROMPT ----------------------------------------------------------
PROMPT  [04] Creating table: SPOC_CONTACTS
PROMPT ----------------------------------------------------------
CREATE TABLE spoc_contacts (
    id         NUMBER        GENERATED ALWAYS AS IDENTITY
                                 (START WITH 1 INCREMENT BY 1) NOT NULL,
    name       VARCHAR2(150)  NOT NULL,
    phone      VARCHAR2(20)   NOT NULL,
    email      VARCHAR2(150),
    location   VARCHAR2(200),
    created_at TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_spoc_contacts PRIMARY KEY (id)
);

PROMPT ----------------------------------------------------------
PROMPT  [05] Creating table: PICKUP_LOCATIONS
PROMPT ----------------------------------------------------------
CREATE TABLE pickup_locations (
    id            NUMBER        GENERATED ALWAYS AS IDENTITY
                                    (START WITH 1 INCREMENT BY 1) NOT NULL,
    name          VARCHAR2(150)  NOT NULL,
    address       VARCHAR2(500)  NOT NULL,
    phone         VARCHAR2(20),
    email         VARCHAR2(150),
    manager_name  VARCHAR2(150),
    location_type VARCHAR2(50)   DEFAULT 'retail',
    capacity      NUMBER(10),
    current_boxes NUMBER(10)     DEFAULT 0,
    is_active     NUMBER(1)      DEFAULT 1,
    notes         VARCHAR2(1000),
    created_at    TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    updated_at    TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_pickup_locations        PRIMARY KEY (id),
    CONSTRAINT chk_pickup_is_active       CHECK       (is_active IN (0, 1)),
    CONSTRAINT chk_pickup_current_boxes   CHECK       (current_boxes >= 0)
);

PROMPT ----------------------------------------------------------
PROMPT  [06] Creating table: PRODUCT_VARIANTS  (FK -> PRODUCTS)
PROMPT ----------------------------------------------------------
CREATE TABLE product_variants (
    id         NUMBER        GENERATED ALWAYS AS IDENTITY
                                 (START WITH 1 INCREMENT BY 1) NOT NULL,
    product_id NUMBER(10)    NOT NULL,
    size_name  VARCHAR2(100) NOT NULL,
    unit       VARCHAR2(50)  NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_product_variants      PRIMARY KEY (id),
    CONSTRAINT uq_pv_product_size       UNIQUE      (product_id, size_name),
    CONSTRAINT fk_pv_product            FOREIGN KEY (product_id)
        REFERENCES products (id) ON DELETE CASCADE
);

PROMPT ----------------------------------------------------------
PROMPT  [07] Creating table: PRICING  (FK -> PRODUCT_VARIANTS)
PROMPT ----------------------------------------------------------
CREATE TABLE pricing (
    id                 NUMBER        GENERATED ALWAYS AS IDENTITY
                                         (START WITH 1 INCREMENT BY 1) NOT NULL,
    product_variant_id NUMBER(10)    NOT NULL,
    base_price         NUMBER(10, 2) NOT NULL,
    currency           VARCHAR2(10)  DEFAULT 'USD',
    valid_from         DATE,
    valid_to           DATE,
    created_at         TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    updated_at         TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_pricing             PRIMARY KEY (id),
    CONSTRAINT fk_pricing_variant     FOREIGN KEY (product_variant_id)
        REFERENCES product_variants (id) ON DELETE CASCADE,
    CONSTRAINT chk_pricing_dates      CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

PROMPT ----------------------------------------------------------
PROMPT  [08] Creating table: STOCK_INVENTORY  (FK -> PRODUCT_VARIANTS)
PROMPT ----------------------------------------------------------
CREATE TABLE stock_inventory (
    id                 NUMBER        GENERATED ALWAYS AS IDENTITY
                                         (START WITH 1 INCREMENT BY 1) NOT NULL,
    product_variant_id NUMBER(10)    NOT NULL,
    quantity_available NUMBER(10)    DEFAULT 0,
    reserved_quantity  NUMBER(10)    DEFAULT 0,
    warehouse_location VARCHAR2(200),
    last_updated       TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_stock_inventory     PRIMARY KEY (id),
    CONSTRAINT uq_si_variant          UNIQUE      (product_variant_id),
    CONSTRAINT fk_si_variant          FOREIGN KEY (product_variant_id)
        REFERENCES product_variants (id) ON DELETE CASCADE,
    CONSTRAINT chk_si_qty_available   CHECK (quantity_available >= 0),
    CONSTRAINT chk_si_qty_reserved    CHECK (reserved_quantity  >= 0)
);

PROMPT ----------------------------------------------------------
PROMPT  [09] Creating table: ORDERS
PROMPT ----------------------------------------------------------
CREATE TABLE orders (
    id                NUMBER        GENERATED ALWAYS AS IDENTITY
                                        (START WITH 1 INCREMENT BY 1) NOT NULL,
    order_ref         VARCHAR2(50)   NOT NULL,
    customer_name     VARCHAR2(150)  NOT NULL,
    customer_email    VARCHAR2(150),
    customer_phone    VARCHAR2(20),
    subtotal          NUMBER(10, 2)  NOT NULL,
    delivery_fee      NUMBER(10, 2)  DEFAULT 0,
    total_price       NUMBER(10, 2)  NOT NULL,
    payment_method    VARCHAR2(50),
    payment_status    VARCHAR2(50)   DEFAULT 'pending',
    payment_intent_id VARCHAR2(300),
    order_status      VARCHAR2(50)   DEFAULT 'pending',
    delivery_address  VARCHAR2(500),
    created_at        TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    updated_at        TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_orders              PRIMARY KEY (id),
    CONSTRAINT uq_orders_ref          UNIQUE      (order_ref),
    CONSTRAINT chk_orders_subtotal    CHECK (subtotal    >= 0),
    CONSTRAINT chk_orders_total       CHECK (total_price >= 0),
    CONSTRAINT chk_orders_del_fee     CHECK (delivery_fee >= 0)
);

PROMPT ----------------------------------------------------------
PROMPT  [10] Creating table: SHIPMENTS  (FK -> PRODUCTS, SPOC_CONTACTS)
PROMPT ----------------------------------------------------------
CREATE TABLE shipments (
    id                      NUMBER        GENERATED ALWAYS AS IDENTITY
                                              (START WITH 1 INCREMENT BY 1) NOT NULL,
    shipment_ref            VARCHAR2(50)   NOT NULL,
    product_id              NUMBER(10)     NOT NULL,
    total_boxes             NUMBER(10)     NOT NULL,
    expected_value          NUMBER(15, 2),
    status                  VARCHAR2(50)   DEFAULT 'pending',
    spoc_contact_id         NUMBER(10),
    received_date           TIMESTAMP WITH TIME ZONE,
    completion_date         TIMESTAMP WITH TIME ZONE,
    notes                   VARCHAR2(1000),
    reception_date          TIMESTAMP WITH TIME ZONE,
    expected_reception_date TIMESTAMP WITH TIME ZONE,
    expected_delivery_date  TIMESTAMP WITH TIME ZONE,
    is_reception_complete   NUMBER(1)      DEFAULT 0,
    total_prebooking_boxes  NUMBER(10)     DEFAULT 0,
    total_pickup_boxes      NUMBER(10)     DEFAULT 0,
    total_pending_boxes     NUMBER(10)     DEFAULT 0,
    total_in_transit_boxes  NUMBER(10)     DEFAULT 0,
    total_delivered_boxes   NUMBER(10)     DEFAULT 0,
    total_missing_boxes     NUMBER(10)     DEFAULT 0,
    total_damaged_boxes     NUMBER(10)     DEFAULT 0,
    total_pending_payment   NUMBER(15, 2)  DEFAULT 0,
    total_collected_payment NUMBER(15, 2)  DEFAULT 0,
    total_partial_payment   NUMBER(15, 2)  DEFAULT 0,
    collection_percentage   NUMBER(5, 2)   DEFAULT 0,
    created_at              TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    updated_at              TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_shipments               PRIMARY KEY (id),
    CONSTRAINT uq_shipments_ref           UNIQUE      (shipment_ref),
    CONSTRAINT fk_shipments_product       FOREIGN KEY (product_id)
        REFERENCES products (id),
    CONSTRAINT fk_shipments_spoc          FOREIGN KEY (spoc_contact_id)
        REFERENCES spoc_contacts (id),
    CONSTRAINT chk_shipments_is_recep     CHECK (is_reception_complete IN (0, 1)),
    CONSTRAINT chk_shipments_total_boxes  CHECK (total_boxes >= 0)
);

PROMPT ----------------------------------------------------------
PROMPT  [11] Creating table: ORDER_ITEMS  (FK -> ORDERS, PRODUCT_VARIANTS)
PROMPT ----------------------------------------------------------
CREATE TABLE order_items (
    id                 NUMBER        GENERATED ALWAYS AS IDENTITY
                                         (START WITH 1 INCREMENT BY 1) NOT NULL,
    order_id           NUMBER(10)    NOT NULL,
    product_variant_id NUMBER(10)    NOT NULL,
    quantity           NUMBER(10)    NOT NULL,
    unit_price         NUMBER(10, 2) NOT NULL,
    subtotal           NUMBER(10, 2) NOT NULL,
    created_at         TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_order_items         PRIMARY KEY (id),
    CONSTRAINT fk_oi_order            FOREIGN KEY (order_id)
        REFERENCES orders (id) ON DELETE CASCADE,
    CONSTRAINT fk_oi_variant          FOREIGN KEY (product_variant_id)
        REFERENCES product_variants (id),
    CONSTRAINT chk_oi_quantity        CHECK (quantity  > 0),
    CONSTRAINT chk_oi_unit_price      CHECK (unit_price >= 0),
    CONSTRAINT chk_oi_subtotal        CHECK (subtotal  >= 0)
);

PROMPT ----------------------------------------------------------
PROMPT  [12] Creating table: SHIPMENT_BOXES
PROMPT        (FK -> SHIPMENTS, PICKUP_LOCATIONS, PRODUCT_VARIANTS)
PROMPT ----------------------------------------------------------
CREATE TABLE shipment_boxes (
    id                   NUMBER        GENERATED ALWAYS AS IDENTITY
                                           (START WITH 1 INCREMENT BY 1) NOT NULL,
    shipment_id          NUMBER(10)    NOT NULL,
    box_number           VARCHAR2(100) NOT NULL,
    quantity_boxes       NUMBER(10)    DEFAULT 1,
    box_status           VARCHAR2(50)  DEFAULT 'in-stock',
    delivery_type        VARCHAR2(50)  DEFAULT 'pending',
    delivery_charge      NUMBER(10, 2) DEFAULT 0,
    receiver_name        VARCHAR2(150),
    receiver_phone       VARCHAR2(20),
    location_id          NUMBER(10),
    delivery_status      VARCHAR2(50)  DEFAULT 'pending',
    payment_status       VARCHAR2(50)  DEFAULT 'pending',
    product_variant_id   NUMBER(10),
    variety_size         VARCHAR2(50),
    quantity_per_variety NUMBER(10)    DEFAULT 1,
    created_at           TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    updated_at           TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_shipment_boxes       PRIMARY KEY (id),
    CONSTRAINT uq_sb_shipment_box      UNIQUE      (shipment_id, box_number),
    CONSTRAINT fk_sb_shipment          FOREIGN KEY (shipment_id)
        REFERENCES shipments (id) ON DELETE CASCADE,
    CONSTRAINT fk_sb_pickup_location   FOREIGN KEY (location_id)
        REFERENCES pickup_locations (id),
    CONSTRAINT fk_sb_variant           FOREIGN KEY (product_variant_id)
        REFERENCES product_variants (id),
    CONSTRAINT chk_sb_qty_boxes        CHECK (quantity_boxes       >= 1),
    CONSTRAINT chk_sb_qty_per_variety  CHECK (quantity_per_variety >= 1),
    CONSTRAINT chk_sb_delivery_charge  CHECK (delivery_charge      >= 0)
);

PROMPT ----------------------------------------------------------
PROMPT  [13] Creating table: DELIVERY_LOGS
PROMPT        (FK -> SHIPMENT_BOXES, LOCATIONS, ORDERS)
PROMPT ----------------------------------------------------------
CREATE TABLE delivery_logs (
    id                 NUMBER        GENERATED ALWAYS AS IDENTITY
                                         (START WITH 1 INCREMENT BY 1) NOT NULL,
    shipment_box_id    NUMBER(10)    NOT NULL,
    location_id        NUMBER(10),
    order_id           NUMBER(10),
    delivery_address   VARCHAR2(500),
    delivery_date      TIMESTAMP WITH TIME ZONE,
    delivery_notes     VARCHAR2(500),
    receiver_name      VARCHAR2(150),
    receiver_phone     VARCHAR2(20),
    is_direct_delivery NUMBER(1)     DEFAULT 0,
    created_at         TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_delivery_logs         PRIMARY KEY (id),
    CONSTRAINT fk_dl_box                FOREIGN KEY (shipment_box_id)
        REFERENCES shipment_boxes (id) ON DELETE CASCADE,
    CONSTRAINT fk_dl_location           FOREIGN KEY (location_id)
        REFERENCES locations (id),
    CONSTRAINT fk_dl_order              FOREIGN KEY (order_id)
        REFERENCES orders (id),
    CONSTRAINT chk_dl_is_direct         CHECK (is_direct_delivery IN (0, 1))
);

PROMPT ----------------------------------------------------------
PROMPT  [14] Creating table: SHIPMENT_SUMMARY  (FK -> SHIPMENTS)
PROMPT ----------------------------------------------------------
CREATE TABLE shipment_summary (
    id                       NUMBER        GENERATED ALWAYS AS IDENTITY
                                               (START WITH 1 INCREMENT BY 1) NOT NULL,
    shipment_id              NUMBER(10)    NOT NULL,
    total_boxes_received     NUMBER(10)    NOT NULL,
    boxes_delivered_direct   NUMBER(10)    DEFAULT 0,
    boxes_collected_self     NUMBER(10)    DEFAULT 0,
    boxes_damaged            NUMBER(10)    DEFAULT 0,
    total_delivery_revenue   NUMBER(15, 2) DEFAULT 0,
    delivery_locations_count NUMBER(10)    DEFAULT 0,
    summary_json             VARCHAR2(4000),
    generated_at             TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_shipment_summary        PRIMARY KEY (id),
    CONSTRAINT uq_ss_shipment             UNIQUE      (shipment_id),
    CONSTRAINT fk_ss_shipment             FOREIGN KEY (shipment_id)
        REFERENCES shipments (id) ON DELETE CASCADE,
    CONSTRAINT chk_ss_boxes_received      CHECK (total_boxes_received   >= 0),
    CONSTRAINT chk_ss_boxes_direct        CHECK (boxes_delivered_direct >= 0),
    CONSTRAINT chk_ss_boxes_self          CHECK (boxes_collected_self   >= 0),
    CONSTRAINT chk_ss_boxes_damaged       CHECK (boxes_damaged          >= 0)
);

PROMPT ----------------------------------------------------------
PROMPT  [15] Creating table: PREBOOKINGS
PROMPT        (FK -> SHIPMENTS, SHIPMENT_BOXES)
PROMPT ----------------------------------------------------------
CREATE TABLE prebookings (
    id                      NUMBER        GENERATED ALWAYS AS IDENTITY
                                              (START WITH 1 INCREMENT BY 1) NOT NULL,
    shipment_id             NUMBER(10)    NOT NULL,
    shipment_box_id         NUMBER(10)    NOT NULL,
    customer_name           VARCHAR2(150) NOT NULL,
    customer_phone          VARCHAR2(20)  NOT NULL,
    customer_email          VARCHAR2(150),
    delivery_address        VARCHAR2(500) NOT NULL,
    booking_date            TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    scheduled_delivery_date TIMESTAMP WITH TIME ZONE,
    status                  VARCHAR2(50)  DEFAULT 'booked',
    created_at              TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    updated_at              TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_prebookings          PRIMARY KEY (id),
    CONSTRAINT fk_pb_shipment          FOREIGN KEY (shipment_id)
        REFERENCES shipments (id) ON DELETE CASCADE,
    CONSTRAINT fk_pb_box               FOREIGN KEY (shipment_box_id)
        REFERENCES shipment_boxes (id) ON DELETE CASCADE
);

PROMPT ----------------------------------------------------------
PROMPT  [16] Creating table: PAYMENT_RECORDS
PROMPT        (FK -> SHIPMENT_BOXES, PREBOOKINGS)
PROMPT ----------------------------------------------------------
CREATE TABLE payment_records (
    id              NUMBER        GENERATED ALWAYS AS IDENTITY
                                      (START WITH 1 INCREMENT BY 1) NOT NULL,
    shipment_box_id NUMBER(10)    NOT NULL,
    prebooking_id   NUMBER(10),
    description     VARCHAR2(500),
    amount          NUMBER(10, 2) NOT NULL,
    payment_status  VARCHAR2(50)  DEFAULT 'pending',
    payment_date    TIMESTAMP WITH TIME ZONE,
    payment_method  VARCHAR2(50),
    transaction_ref VARCHAR2(150),
    notes           VARCHAR2(500),
    created_at      TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_payment_records      PRIMARY KEY (id),
    CONSTRAINT fk_pr_box               FOREIGN KEY (shipment_box_id)
        REFERENCES shipment_boxes (id) ON DELETE CASCADE,
    CONSTRAINT fk_pr_prebooking        FOREIGN KEY (prebooking_id)
        REFERENCES prebookings (id) ON DELETE SET NULL,
    CONSTRAINT chk_pr_amount           CHECK (amount >= 0)
);

PROMPT ----------------------------------------------------------
PROMPT  [17] Creating table: BOX_ENTRY_LOGS
PROMPT        (FK -> SHIPMENT_BOXES, ADMIN_USERS)
PROMPT ----------------------------------------------------------
CREATE TABLE box_entry_logs (
    id              NUMBER        GENERATED ALWAYS AS IDENTITY
                                      (START WITH 1 INCREMENT BY 1) NOT NULL,
    shipment_box_id NUMBER(10)    NOT NULL,
    entry_type      VARCHAR2(50),
    old_value       VARCHAR2(500),
    new_value       VARCHAR2(500),
    changed_by      NUMBER(10),
    created_at      TIMESTAMP WITH TIME ZONE  DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_box_entry_logs       PRIMARY KEY (id),
    CONSTRAINT fk_bel_box              FOREIGN KEY (shipment_box_id)
        REFERENCES shipment_boxes (id) ON DELETE CASCADE,
    CONSTRAINT fk_bel_admin            FOREIGN KEY (changed_by)
        REFERENCES admin_users (id) ON DELETE SET NULL
);

PROMPT ----------------------------------------------------------
PROMPT  All 17 tables created successfully.
PROMPT ----------------------------------------------------------
