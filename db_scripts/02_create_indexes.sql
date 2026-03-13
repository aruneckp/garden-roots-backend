-- ============================================================
-- Garden Roots - Create Indexes
-- Database : Oracle 12c+  (XE / XEPDB1)
-- Notes    :
--   • PRIMARY KEY and UNIQUE constraints already create indexes
--     automatically – they are NOT repeated here.
--   • Only non-unique performance indexes are created here,
--     matching the index=True columns in models.py.
-- ============================================================

WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

PROMPT Creating indexes for PRODUCT_VARIANTS ...
CREATE INDEX idx_pv_product_id        ON product_variants   (product_id);

PROMPT Creating indexes for PRICING ...
CREATE INDEX idx_pricing_variant_id   ON pricing            (product_variant_id);

PROMPT Creating indexes for ORDERS ...
CREATE INDEX idx_orders_payment_status ON orders            (payment_status);
CREATE INDEX idx_orders_order_status   ON orders            (order_status);

PROMPT Creating indexes for SHIPMENTS ...
CREATE INDEX idx_shipments_status      ON shipments         (status);

PROMPT Creating indexes for ORDER_ITEMS ...
CREATE INDEX idx_oi_order_id           ON order_items       (order_id);
CREATE INDEX idx_oi_variant_id         ON order_items       (product_variant_id);

PROMPT Creating indexes for SHIPMENT_BOXES ...
-- Note: (shipment_id, box_number) UNIQUE index already covers leading
--       shipment_id lookups, so we only add the status indexes.
CREATE INDEX idx_sb_box_status         ON shipment_boxes    (box_status);
CREATE INDEX idx_sb_delivery_status    ON shipment_boxes    (delivery_status);
CREATE INDEX idx_sb_payment_status     ON shipment_boxes    (payment_status);

PROMPT Creating indexes for DELIVERY_LOGS ...
CREATE INDEX idx_dl_shipment_box_id    ON delivery_logs     (shipment_box_id);

PROMPT Creating indexes for PICKUP_LOCATIONS ...
CREATE INDEX idx_pl_name               ON pickup_locations  (name);
CREATE INDEX idx_pl_is_active          ON pickup_locations  (is_active);

PROMPT Creating indexes for PREBOOKINGS ...
CREATE INDEX idx_pb_shipment_id        ON prebookings       (shipment_id);
CREATE INDEX idx_pb_shipment_box_id    ON prebookings       (shipment_box_id);
CREATE INDEX idx_pb_status             ON prebookings       (status);

PROMPT Creating indexes for PAYMENT_RECORDS ...
CREATE INDEX idx_pr_shipment_box_id    ON payment_records   (shipment_box_id);
CREATE INDEX idx_pr_payment_status     ON payment_records   (payment_status);

PROMPT Creating indexes for BOX_ENTRY_LOGS ...
CREATE INDEX idx_bel_shipment_box_id   ON box_entry_logs    (shipment_box_id);
CREATE INDEX idx_bel_entry_type        ON box_entry_logs    (entry_type);

PROMPT ----------------------------------------------------------
PROMPT  All indexes created successfully.
PROMPT ----------------------------------------------------------
