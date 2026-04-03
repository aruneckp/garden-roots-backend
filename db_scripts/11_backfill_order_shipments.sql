-- =============================================================
-- Script  : 11_backfill_order_shipments.sql
-- Purpose : Back-fill shipment_id on existing orders that have
--           NULL shipment_id.
--
-- Strategy: For each null order, find the most recent shipment
--           whose created_at <= order.created_at (i.e. the
--           shipment that was "live" when the order was placed).
--           If no earlier shipment exists, assign the oldest one.
-- =============================================================

UPDATE orders o
SET o.shipment_id = NVL(
    -- nearest shipment created at or before this order
    (SELECT s.id FROM shipments s
      WHERE s.created_at <= o.created_at
      ORDER BY s.created_at DESC
      FETCH FIRST 1 ROWS ONLY),
    -- fallback: oldest shipment in the system
    (SELECT s.id FROM shipments s
      ORDER BY s.created_at ASC
      FETCH FIRST 1 ROWS ONLY)
)
WHERE o.shipment_id IS NULL;

COMMIT;

-- Verify
SELECT COUNT(*) AS still_null FROM orders WHERE shipment_id IS NULL;
