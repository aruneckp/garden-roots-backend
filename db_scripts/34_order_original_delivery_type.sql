-- ============================================================
-- Migration 34: Track original delivery type on ORDERS
-- Allows the admin UI to show an indicator when an order was
-- placed as self-collection but later changed to home delivery.
-- Set once at order creation; never updated by admin edits.
-- ============================================================

ALTER TABLE orders
    ADD original_delivery_type VARCHAR2(20);

-- Back-fill existing rows: assume current delivery_type was the original
UPDATE orders
   SET original_delivery_type = delivery_type
 WHERE original_delivery_type IS NULL;

COMMIT;
