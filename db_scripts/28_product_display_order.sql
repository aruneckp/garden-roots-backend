-- Migration 28: Add display_order to products table
-- Controls the order varieties appear on the home screen.
-- Run once against your Oracle DB.

ALTER TABLE products ADD display_order NUMBER(6) DEFAULT 0 NOT NULL;

-- Seed initial order to match current ID order so existing products
-- keep their relative sequence after the migration.
UPDATE products SET display_order = id;

COMMIT;
