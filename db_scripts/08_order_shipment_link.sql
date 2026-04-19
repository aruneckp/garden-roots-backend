-- Migration 08: Add shipment_id to orders for reconciliation
-- Nullable FK to shipments; can be set manually by admin or during reconciliation.

ALTER TABLE orders ADD shipment_id NUMBER;

ALTER TABLE orders ADD CONSTRAINT fk_orders_shipment
    FOREIGN KEY (shipment_id) REFERENCES shipments (id);

CREATE INDEX idx_orders_shipment_id ON orders (shipment_id);

COMMIT;
