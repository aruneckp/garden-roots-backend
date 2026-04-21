-- ============================================================
-- Migration 21: Delivery Tags
-- Creates delivery_tags table and adds delivery_tag_id FK
-- column to orders.
-- ============================================================

--PROMPT ----------------------------------------------------------
--PROMPT  [21-1] Creating table: DELIVERY_TAGS
--PROMPT ----------------------------------------------------------
CREATE TABLE delivery_tags (
    id         NUMBER GENERATED ALWAYS AS IDENTITY NOT NULL,
    name       VARCHAR2(100)  NOT NULL,
    color      VARCHAR2(20)   DEFAULT '#6b7280',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_delivery_tags      PRIMARY KEY (id),
    CONSTRAINT uq_delivery_tags_name UNIQUE (name).  
);

--PROMPT ----------------------------------------------------------
--PROMPT  [21-2] Adding delivery_tag_id FK column to ORDERS
--PROMPT ----------------------------------------------------------
ALTER TABLE orders ADD delivery_tag_id NUMBER;

ALTER TABLE orders ADD CONSTRAINT fk_orders_delivery_tag
    FOREIGN KEY (delivery_tag_id) REFERENCES delivery_tags(id);

CREATE INDEX idx_orders_delivery_tag_id ON orders (delivery_tag_id);

--PROMPT ----------------------------------------------------------
--PROMPT  [21] Migration complete.
--PROMPT ----------------------------------------------------------
