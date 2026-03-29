-- ============================================================================
-- Migration 06: Add delivery_type, pickup_location, and customer_notes
--               to orders; add whatsapp_phone to pickup_locations
-- Run once against the existing schema (after migration 05).
-- ============================================================================

-- 1. delivery_type: 'delivery' (home) or 'pickup' (self-collect)
ALTER TABLE orders ADD delivery_type VARCHAR2(20) DEFAULT 'delivery';
ALTER TABLE orders ADD CONSTRAINT chk_orders_delivery_type
    CHECK (delivery_type IN ('delivery', 'pickup'));

-- 2. FK to the pickup location chosen when delivery_type = 'pickup'
ALTER TABLE orders ADD pickup_location_id NUMBER;
ALTER TABLE orders ADD CONSTRAINT fk_orders_pickup_location
    FOREIGN KEY (pickup_location_id) REFERENCES pickup_locations (id)
    ON DELETE SET NULL;

-- 3. Optional notes / feedback the customer can leave per order
ALTER TABLE orders ADD customer_notes VARCHAR2(1000);

-- 4. WhatsApp contact for each pickup location (shown in checkout)
ALTER TABLE pickup_locations ADD whatsapp_phone VARCHAR2(20);

-- Indexes
CREATE INDEX idx_orders_delivery_type       ON orders (delivery_type);
CREATE INDEX idx_orders_pickup_location_id  ON orders (pickup_location_id);

COMMIT;
