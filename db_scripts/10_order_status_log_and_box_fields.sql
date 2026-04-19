-- =============================================================
-- Script  : 10_order_status_log_and_box_fields.sql
-- Purpose : (a) Add box_weight and price_per_kg to shipment_boxes
--           (b) Create order_status_logs audit table
-- =============================================================

--PROMPT ----------------------------------------------------------
--PROMPT  [10-1] Adding box_weight and price_per_kg to SHIPMENT_BOXES
--PROMPT ----------------------------------------------------------
ALTER TABLE shipment_boxes ADD box_weight   NUMBER(8,2);
ALTER TABLE shipment_boxes ADD price_per_kg NUMBER(10,2);

--PROMPT ----------------------------------------------------------
--PROMPT  [10-2] Creating ORDER_STATUS_LOGS audit table
--PROMPT ----------------------------------------------------------
CREATE TABLE order_status_logs (
    id          NUMBER GENERATED ALWAYS AS IDENTITY NOT NULL,
    order_id    NUMBER                              NOT NULL,
    old_status  VARCHAR2(50),
    new_status  VARCHAR2(50)                        NOT NULL,
    changed_by  NUMBER,
    note        VARCHAR2(500),
    changed_at  TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_order_status_logs  PRIMARY KEY (id),
    CONSTRAINT fk_osl_order          FOREIGN KEY (order_id)
        REFERENCES orders (id) ON DELETE CASCADE,
    CONSTRAINT fk_osl_admin          FOREIGN KEY (changed_by)
        REFERENCES admin_users (id)
);

CREATE INDEX idx_order_status_logs_order_id ON order_status_logs (order_id);
CREATE INDEX idx_order_status_logs_changed_by ON order_status_logs (changed_by);

COMMIT;
