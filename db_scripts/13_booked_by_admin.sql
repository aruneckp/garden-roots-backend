-- ============================================================
-- Migration 13: Track which admin booked a pay_later order
-- Adds booked_by_admin_id and booked_by_admin_name to orders.
-- No FK constraint since admins may exist in either admin_users
-- or users (Google OAuth) table.
-- ============================================================

--PROMPT ----------------------------------------------------------
--PROMPT  [13-1] Adding BOOKED_BY_ADMIN_ID to ORDERS
--PROMPT ----------------------------------------------------------
ALTER TABLE orders ADD booked_by_admin_id NUMBER;

--PROMPT ----------------------------------------------------------
--PROMPT  [13-2] Adding BOOKED_BY_ADMIN_NAME to ORDERS
--PROMPT ----------------------------------------------------------
ALTER TABLE orders ADD booked_by_admin_name VARCHAR2(150);

CREATE INDEX idx_orders_booked_by_admin ON orders (booked_by_admin_id);

COMMIT;
