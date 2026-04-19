-- Migration: clear 'Box of 6' size_name from all product variants
-- Replace with 'Standard' since size_name is NOT NULL
UPDATE product_variants SET size_name = 'Standard' WHERE size_name = 'Box of 6';
COMMIT;
