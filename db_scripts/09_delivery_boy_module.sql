-- ============================================================
-- Migration 09: Delivery Boy Module
-- Creates delivery_boys table and adds delivery assignment
-- columns to orders.
-- ============================================================

--PROMPT ----------------------------------------------------------
--PROMPT  [09-1] Creating table: DELIVERY_BOYS
--PROMPT ----------------------------------------------------------
CREATE TABLE delivery_boys (
    id            NUMBER GENERATED ALWAYS AS IDENTITY NOT NULL,
    username      VARCHAR2(100)  NOT NULL,
    password_hash VARCHAR2(255)  NOT NULL,
    full_name     VARCHAR2(150),
    phone         VARCHAR2(20),
    is_active     NUMBER(1)      DEFAULT 1,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP,
    updated_at    TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_delivery_boys      PRIMARY KEY (id),
    CONSTRAINT uq_delivery_boys_user UNIQUE (username)
);

CREATE INDEX idx_delivery_boys_username ON delivery_boys (username);

--PROMPT ----------------------------------------------------------
--PROMPT  [09-2] Adding delivery assignment columns to ORDERS
--PROMPT ----------------------------------------------------------
ALTER TABLE orders ADD delivery_boy_id NUMBER;
ALTER TABLE orders ADD delivery_code   VARCHAR2(50);
ALTER TABLE orders ADD assigned_at     TIMESTAMP WITH TIME ZONE;

ALTER TABLE orders ADD CONSTRAINT fk_orders_delivery_boy
    FOREIGN KEY (delivery_boy_id) REFERENCES delivery_boys (id) ON DELETE SET NULL;

CREATE INDEX idx_orders_delivery_boy_id ON orders (delivery_boy_id);

COMMIT;
