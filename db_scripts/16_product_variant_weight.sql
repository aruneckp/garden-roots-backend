-- ============================================================
-- Migration 16: Add box_weight to product_variants
-- Stores the weight per box (kg) directly on the variant so
-- the storefront can display it without static fallback data.
-- ============================================================

ALTER TABLE product_variants ADD box_weight NUMBER(8, 2);

COMMENT ON COLUMN product_variants.box_weight IS 'Weight of one box in kg (e.g. 3.2 for a 3.2 kg box)';

COMMIT;
