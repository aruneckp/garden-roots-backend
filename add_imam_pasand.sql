-- Add Imam Pasand mango variety
-- Safe to re-run: uses MERGE to avoid duplicates

-- 1. Product
MERGE INTO products p
USING (SELECT 'Imam Pasand' AS name FROM DUAL) src
ON (p.name = src.name)
WHEN NOT MATCHED THEN
    INSERT (name, description, origin, season_start, season_end, tag)
    VALUES (
        'Imam Pasand',
        'An elegant royal variety from Telangana with melting texture and rich, nuanced sweetness. Known as the mango of the Nawabs.',
        'Telangana',
        'May',
        'Jun',
        'Royal'
    );

-- 2. Variants
MERGE INTO product_variants pv
USING (
    SELECT id AS product_id FROM products WHERE name = 'Imam Pasand'
) src
ON (pv.product_id = src.product_id AND pv.size_name = 'Box of 6')
WHEN NOT MATCHED THEN
    INSERT (product_id, size_name, unit)
    VALUES (src.product_id, 'Box of 6', 'box');

MERGE INTO product_variants pv
USING (
    SELECT id AS product_id FROM products WHERE name = 'Imam Pasand'
) src
ON (pv.product_id = src.product_id AND pv.size_name = 'Box of 12')
WHEN NOT MATCHED THEN
    INSERT (product_id, size_name, unit)
    VALUES (src.product_id, 'Box of 12', 'box');

-- 3. Pricing (Box of 6 = $50, Box of 12 = $92)
MERGE INTO pricing pr
USING (
    SELECT pv.id AS variant_id FROM product_variants pv
    JOIN products p ON p.id = pv.product_id
    WHERE p.name = 'Imam Pasand' AND pv.size_name = 'Box of 6'
) src
ON (pr.product_variant_id = src.variant_id)
WHEN NOT MATCHED THEN
    INSERT (product_variant_id, base_price, currency, valid_from)
    VALUES (src.variant_id, 50.00, 'USD', TRUNC(SYSDATE));

MERGE INTO pricing pr
USING (
    SELECT pv.id AS variant_id FROM product_variants pv
    JOIN products p ON p.id = pv.product_id
    WHERE p.name = 'Imam Pasand' AND pv.size_name = 'Box of 12'
) src
ON (pr.product_variant_id = src.variant_id)
WHEN NOT MATCHED THEN
    INSERT (product_variant_id, base_price, currency, valid_from)
    VALUES (src.variant_id, 92.00, 'USD', TRUNC(SYSDATE));

-- 4. Stock inventory (Box of 6 = 80 units, Box of 12 = 50 units)
MERGE INTO stock_inventory si
USING (
    SELECT pv.id AS variant_id FROM product_variants pv
    JOIN products p ON p.id = pv.product_id
    WHERE p.name = 'Imam Pasand' AND pv.size_name = 'Box of 6'
) src
ON (si.product_variant_id = src.variant_id)
WHEN NOT MATCHED THEN
    INSERT (product_variant_id, quantity_available, warehouse_location)
    VALUES (src.variant_id, 80, 'Main Warehouse - Singapore');

MERGE INTO stock_inventory si
USING (
    SELECT pv.id AS variant_id FROM product_variants pv
    JOIN products p ON p.id = pv.product_id
    WHERE p.name = 'Imam Pasand' AND pv.size_name = 'Box of 12'
) src
ON (si.product_variant_id = src.variant_id)
WHEN NOT MATCHED THEN
    INSERT (product_variant_id, quantity_available, warehouse_location)
    VALUES (src.variant_id, 50, 'Main Warehouse - Singapore');

COMMIT;
