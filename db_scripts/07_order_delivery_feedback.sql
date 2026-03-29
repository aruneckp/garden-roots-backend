-- ============================================================================
-- Migration 07: Add delivery_feedback to orders
--
-- Customers can leave post-delivery comments on any paid order:
--   - Was there an issue with the delivery?
--   - Any general feedback for the team?
-- Visible to both customer (My Bookings) and admin (order detail view).
-- ============================================================================

ALTER TABLE orders ADD delivery_feedback VARCHAR2(2000);

COMMIT;
