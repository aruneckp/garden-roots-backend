-- Garden Roots Seed Data
-- Sample product data for mango varieties, variants, pricing, stock, and locations

-- PRODUCTS
INSERT INTO products (name, description, origin, season_start, season_end, tag)
VALUES (
    'Alphonso',
    'The king of mangoes. Buttery texture, rich sweetness, and distinctive aroma make this the most sought-after variety.',
    'Ratnagiri, Maharashtra',
    'Apr',
    'Jun',
    'Premium'
);

INSERT INTO products (name, description, origin, season_start, season_end, tag)
VALUES (
    'Mallika',
    'Known for its consistent quality and excellent shelf life. Sweet flesh with a mild fragrance.',
    'Andhra Pradesh',
    'May',
    'Jul',
    'Popular'
);

INSERT INTO products (name, description, origin, season_start, season_end, tag)
VALUES (
    'Banganapalli',
    'Golden yellow color with smooth texture. Perfect for fresh consumption and export markets.',
    'Andhra Pradesh',
    'Apr',
    'Jun',
    'Classic'
);

-- PRODUCT VARIANTS (Box sizes - each variant gets stock and pricing)
INSERT INTO product_variants (product_id, size_name, unit)
VALUES ((SELECT id FROM products WHERE name = 'Alphonso'), 'Box of 6', 'box');

INSERT INTO product_variants (product_id, size_name, unit)
VALUES ((SELECT id FROM products WHERE name = 'Alphonso'), 'Box of 12', 'box');

INSERT INTO product_variants (product_id, size_name, unit)
VALUES ((SELECT id FROM products WHERE name = 'Mallika'), 'Box of 6', 'box');

INSERT INTO product_variants (product_id, size_name, unit)
VALUES ((SELECT id FROM products WHERE name = 'Mallika'), 'Box of 12', 'box');

INSERT INTO product_variants (product_id, size_name, unit)
VALUES ((SELECT id FROM products WHERE name = 'Banganapalli'), 'Box of 6', 'box');

INSERT INTO product_variants (product_id, size_name, unit)
VALUES ((SELECT id FROM products WHERE name = 'Banganapalli'), 'Box of 12', 'box');

-- PRICING (Current pricing - corresponds to frontend prices)
-- Alphonso Box of 6 = $32
INSERT INTO pricing (product_variant_id, base_price, currency, valid_from)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Alphonso') AND size_name = 'Box of 6'),
    32.00,
    'USD',
    TRUNC(SYSDATE)
);

-- Alphonso Box of 12 = $58
INSERT INTO pricing (product_variant_id, base_price, currency, valid_from)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Alphonso') AND size_name = 'Box of 12'),
    58.00,
    'USD',
    TRUNC(SYSDATE)
);

-- Mallika Box of 6 = $38
INSERT INTO pricing (product_variant_id, base_price, currency, valid_from)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Mallika') AND size_name = 'Box of 6'),
    38.00,
    'USD',
    TRUNC(SYSDATE)
);

-- Mallika Box of 12 = $68
INSERT INTO pricing (product_variant_id, base_price, currency, valid_from)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Mallika') AND size_name = 'Box of 12'),
    68.00,
    'USD',
    TRUNC(SYSDATE)
);

-- Banganapalli Box of 6 = $33
INSERT INTO pricing (product_variant_id, base_price, currency, valid_from)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Banganapalli') AND size_name = 'Box of 6'),
    33.00,
    'USD',
    TRUNC(SYSDATE)
);

-- Banganapalli Box of 12 = $60
INSERT INTO pricing (product_variant_id, base_price, currency, valid_from)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Banganapalli') AND size_name = 'Box of 12'),
    60.00,
    'USD',
    TRUNC(SYSDATE)
);

-- STOCK INVENTORY (Initial stock levels)
INSERT INTO stock_inventory (product_variant_id, quantity_available, warehouse_location)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Alphonso') AND size_name = 'Box of 6'),
    150,
    'Main Warehouse - Singapore'
);

INSERT INTO stock_inventory (product_variant_id, quantity_available, warehouse_location)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Alphonso') AND size_name = 'Box of 12'),
    100,
    'Main Warehouse - Singapore'
);

INSERT INTO stock_inventory (product_variant_id, quantity_available, warehouse_location)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Mallika') AND size_name = 'Box of 6'),
    180,
    'Main Warehouse - Singapore'
);

INSERT INTO stock_inventory (product_variant_id, quantity_available, warehouse_location)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Mallika') AND size_name = 'Box of 12'),
    120,
    'Main Warehouse - Singapore'
);

INSERT INTO stock_inventory (product_variant_id, quantity_available, warehouse_location)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Banganapalli') AND size_name = 'Box of 6'),
    160,
    'Main Warehouse - Singapore'
);

INSERT INTO stock_inventory (product_variant_id, quantity_available, warehouse_location)
VALUES (
    (SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Banganapalli') AND size_name = 'Box of 12'),
    110,
    'Main Warehouse - Singapore'
);

-- PICKUP LOCATIONS (Singapore locations)
INSERT INTO locations (location_name, address, latitude, longitude, operating_hours)
VALUES (
    'Punggol Hub',
    '1 Punggol Central, Singapore 828649',
    1.4043,
    103.9036,
    '9:00 AM - 6:00 PM'
);

INSERT INTO locations (location_name, address, latitude, longitude, operating_hours)
VALUES (
    'Tampines Center',
    '1 Tampines Central 6, Singapore 529540',
    1.3521,
    103.9426,
    '9:00 AM - 6:00 PM'
);

INSERT INTO locations (location_name, address, latitude, longitude, operating_hours)
VALUES (
    'Sengkang Point',
    '2 Sengkang Square, Singapore 545131',
    1.3766,
    103.8933,
    '9:00 AM - 6:00 PM'
);

COMMIT;
