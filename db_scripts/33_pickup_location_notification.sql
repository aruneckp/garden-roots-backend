-- ============================================================
-- Migration 33: Add notification_message to PICKUP_LOCATIONS
-- Allows admins to set a per-location notice shown to customers
-- when they select that self-collection point at checkout.
-- ============================================================

ALTER TABLE pickup_locations
    ADD notification_message VARCHAR2(500);

COMMIT;
