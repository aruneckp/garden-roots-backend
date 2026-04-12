-- ============================================================
-- Migration 14: Add is_active flag to products table
-- Enables admins to enable / disable products in the catalogue.
-- ============================================================

--PROMPT ----------------------------------------------------------
--PROMPT  [14-1] Adding IS_ACTIVE column to PRODUCTS
--PROMPT ----------------------------------------------------------
ALTER TABLE products ADD is_active NUMBER(1) DEFAULT 1 NOT NULL;

--PROMPT ----------------------------------------------------------
--PROMPT  [14-2] Backfill: ensure all existing products are enabled
--PROMPT ----------------------------------------------------------
UPDATE products SET is_active = 1 WHERE is_active IS NULL OR is_active != 1;

COMMIT;
