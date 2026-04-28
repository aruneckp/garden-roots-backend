-- Migration 25: Order action type config table and per-order action log
-- order_action_types  – lookup/config table, seeded with known action codes
-- order_action_logs   – one row per user action on any order

-- ── Config table ──────────────────────────────────────────────────────────────
CREATE TABLE order_action_types (
    id          NUMBER GENERATED ALWAYS AS IDENTITY NOT NULL,
    code        VARCHAR2(50)  NOT NULL,
    label       VARCHAR2(100) NOT NULL,
    description VARCHAR2(500),
    color       VARCHAR2(20)  DEFAULT '#6b7280',
    icon        VARCHAR2(50),
    is_active   NUMBER(1)     DEFAULT 1 NOT NULL,
    sort_order  NUMBER        DEFAULT 0,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_order_action_types PRIMARY KEY (id),
    CONSTRAINT uq_order_action_types_code UNIQUE (code)
);

-- Seed action types
INSERT INTO order_action_types (code, label, description, color, icon, sort_order)
    VALUES ('ORDER_CREATED',       'Order Created',          'A new order was placed',                                           '#22c55e', 'create',   1);
INSERT INTO order_action_types (code, label, description, color, icon, sort_order)
    VALUES ('STATUS_UPDATE',       'Status Update',          'Order status was changed',                                         '#3b82f6', 'status',   2);
INSERT INTO order_action_types (code, label, description, color, icon, sort_order)
    VALUES ('PAYMENT_UPDATE',      'Payment Update',         'Payment status was updated',                                       '#10b981', 'payment',  3);
INSERT INTO order_action_types (code, label, description, color, icon, sort_order)
    VALUES ('PAYMENT_COLLECTED',   'Payment Collected',      'Cash payment was collected by admin',                              '#059669', 'collect',  4);
INSERT INTO order_action_types (code, label, description, color, icon, sort_order)
    VALUES ('ITEMS_UPDATED',       'Items Updated',          'Order items were added, removed, or quantities changed',           '#f59e0b', 'items',    5);
INSERT INTO order_action_types (code, label, description, color, icon, sort_order)
    VALUES ('CUSTOMER_INFO_UPDATE','Customer Info Updated',  'Customer name, email, or phone was updated',                      '#8b5cf6', 'customer', 6);
INSERT INTO order_action_types (code, label, description, color, icon, sort_order)
    VALUES ('DELIVERY_UPDATE',     'Delivery Updated',       'Delivery address, type, or pickup location was changed',          '#14b8a6', 'delivery', 7);
INSERT INTO order_action_types (code, label, description, color, icon, sort_order)
    VALUES ('NOTES_UPDATED',       'Notes Updated',          'Customer notes were updated',                                     '#f97316', 'notes',    8);
INSERT INTO order_action_types (code, label, description, color, icon, sort_order)
    VALUES ('ORDER_CANCELLED',     'Order Cancelled',        'Order was cancelled',                                             '#ef4444', 'cancel',   9);

COMMIT;

-- ── Action log table ──────────────────────────────────────────────────────────
CREATE TABLE order_action_logs (
    id                    NUMBER GENERATED ALWAYS AS IDENTITY NOT NULL,
    order_id              NUMBER        NOT NULL,
    action_type_id        NUMBER        NOT NULL,
    performed_by          VARCHAR2(150),
    performed_by_admin_id NUMBER,
    details               CLOB,
    note                  VARCHAR2(1000),
    created_at            TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_order_action_logs    PRIMARY KEY (id),
    CONSTRAINT fk_oal_order            FOREIGN KEY (order_id)       REFERENCES orders(id)              ON DELETE CASCADE,
    CONSTRAINT fk_oal_action_type      FOREIGN KEY (action_type_id) REFERENCES order_action_types(id)
);

CREATE INDEX idx_oal_order_id    ON order_action_logs (order_id);
CREATE INDEX idx_oal_type_id     ON order_action_logs (action_type_id);
CREATE INDEX idx_oal_created_at  ON order_action_logs (created_at);
CREATE INDEX idx_oal_admin_id    ON order_action_logs (performed_by_admin_id);
