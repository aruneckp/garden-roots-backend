-- ============================================================
-- METADATA INSERT SCRIPT
-- Generated: 2026-03-31
-- Tables: products, product_variants, pricing, stock_inventory, locations, pickup_locations, admin_users, spoc_contacts
-- ============================================================

-- ------------------------------------------------------------
-- PRODUCTS (4 rows)
-- ------------------------------------------------------------
INSERT INTO products (name, description, origin, season_start, season_end, tag) VALUES ('Alphonso', 'The king of mangoes. Buttery texture, rich sweetness, and distinctive aroma make this the most sought-after variety.', 'Ratnagiri, Maharashtra', 'Apr', 'Jun', 'Premium');
INSERT INTO products (name, description, origin, season_start, season_end, tag) VALUES ('Mallika', 'Known for its consistent quality and excellent shelf life. Sweet flesh with a mild fragrance.', 'Andhra Pradesh', 'May', 'Jul', 'Popular');
INSERT INTO products (name, description, origin, season_start, season_end, tag) VALUES ('Banganapalli', 'Golden yellow color with smooth texture. Perfect for fresh consumption and export markets.', 'Andhra Pradesh', 'Apr', 'Jun', 'Classic');
INSERT INTO products (name, description, origin, season_start, season_end, tag) VALUES ('Imam Pasand', 'An elegant royal variety from Telangana with melting texture and rich, nuanced sweetness. Known as the mango of the Nawabs.', 'Telangana', 'May', 'Jun', 'Royal');
COMMIT;

-- ------------------------------------------------------------
-- PRODUCT_VARIANTS (4 rows)
-- NOTE: product_id references the new IDs generated above
-- Run: SELECT id, name FROM products ORDER BY name; to confirm IDs before inserting
-- ------------------------------------------------------------
INSERT INTO product_variants (product_id, size_name, unit) VALUES ((SELECT id FROM products WHERE name = 'Alphonso'), 'Box of 6', 'box');
INSERT INTO product_variants (product_id, size_name, unit) VALUES ((SELECT id FROM products WHERE name = 'Mallika'), 'Box of 6', 'box');
INSERT INTO product_variants (product_id, size_name, unit) VALUES ((SELECT id FROM products WHERE name = 'Banganapalli'), 'Box of 6', 'box');
INSERT INTO product_variants (product_id, size_name, unit) VALUES ((SELECT id FROM products WHERE name = 'Imam Pasand'), 'Box of 6', 'box');
COMMIT;

-- ------------------------------------------------------------
-- PRICING (4 rows — latest price per variant)
-- ------------------------------------------------------------
INSERT INTO pricing (product_variant_id, base_price, currency, valid_from) VALUES ((SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Alphonso')), 32.0, 'USD', TIMESTAMP '2026-03-08 00:00:00.000000');
INSERT INTO pricing (product_variant_id, base_price, currency, valid_from) VALUES ((SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Mallika')), 38.0, 'USD', TIMESTAMP '2026-03-08 00:00:00.000000');
INSERT INTO pricing (product_variant_id, base_price, currency, valid_from) VALUES ((SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Banganapalli')), 33.0, 'USD', TIMESTAMP '2026-03-08 00:00:00.000000');
INSERT INTO pricing (product_variant_id, base_price, currency, valid_from) VALUES ((SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Imam Pasand')), 50.0, 'USD', TIMESTAMP '2026-03-09 00:00:00.000000');
COMMIT;

-- ------------------------------------------------------------
-- STOCK_INVENTORY (4 rows)
-- ------------------------------------------------------------
INSERT INTO stock_inventory (product_variant_id, quantity_available, reserved_quantity, warehouse_location) VALUES ((SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Alphonso')), 147, 13, 'Main Warehouse - Singapore');
INSERT INTO stock_inventory (product_variant_id, quantity_available, reserved_quantity, warehouse_location) VALUES ((SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Mallika')), 177, 19, 'Main Warehouse - Singapore');
INSERT INTO stock_inventory (product_variant_id, quantity_available, reserved_quantity, warehouse_location) VALUES ((SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Banganapalli')), 157, 12, 'Main Warehouse - Singapore');
INSERT INTO stock_inventory (product_variant_id, quantity_available, reserved_quantity, warehouse_location) VALUES ((SELECT id FROM product_variants WHERE product_id = (SELECT id FROM products WHERE name = 'Imam Pasand')), 77, 6, 'Main Warehouse - Singapore');
COMMIT;

-- ------------------------------------------------------------
-- LOCATIONS (3 rows — deduplicated)
-- ------------------------------------------------------------
INSERT INTO locations (location_name, address, latitude, longitude, operating_hours) VALUES ('Punggol Hub', '1 Punggol Central, Singapore 828649', 1.4043, 103.9036, '9:00 AM - 6:00 PM');
INSERT INTO locations (location_name, address, latitude, longitude, operating_hours) VALUES ('Tampines Center', '1 Tampines Central 6, Singapore 529540', 1.3521, 103.9426, '9:00 AM - 6:00 PM');
INSERT INTO locations (location_name, address, latitude, longitude, operating_hours) VALUES ('Sengkang Point', '2 Sengkang Square, Singapore 545131', 1.3766, 103.8933, '9:00 AM - 6:00 PM');
COMMIT;

-- ------------------------------------------------------------
-- PICKUP_LOCATIONS (3 rows)
-- ------------------------------------------------------------
INSERT INTO pickup_locations (name, address, phone, email, manager_name, location_type, capacity, current_boxes, is_active) VALUES ('Punggol', 'Blk-679A, Damai MRT, Singapore 819862', '65-91234567', 'punggol@garden-roots.sg', 'Venkat', 'retail', 50, 0, 1);
INSERT INTO pickup_locations (name, address, phone, email, manager_name, location_type, capacity, current_boxes, is_active) VALUES ('Tampines West', 'Blk 929, Tampines Street 91, #13-443, Singapore 520929', '65-98346177', 'tampines@garden-roots.sg', 'Venky', 'retail', 75, 0, 1);
INSERT INTO pickup_locations (name, address, phone, email, manager_name, location_type, capacity, current_boxes, is_active) VALUES ('Sengkang', 'Rivervale Link, Singapore 838896', '65-96785432', 'sengkang@garden-roots.sg', 'Amit', 'retail', 60, 0, 1);
COMMIT;

-- ------------------------------------------------------------
-- ADMIN_USERS (1 row)
-- ------------------------------------------------------------
INSERT INTO admin_users (username, password_hash, full_name, email, role, is_active) VALUES ('admin', '$2b$12$iP.kngiywR9mRHk6EN.QyejAGLUrM7iYzGKkOfyOYFbdMDmp3WDaO', 'Admin User', 'admin@gardenroots.com', 'admin', 1);
COMMIT;

-- ------------------------------------------------------------
-- SPOC_CONTACTS (4 rows)
-- ------------------------------------------------------------
INSERT INTO spoc_contacts (name, phone, email, location) VALUES ('Rajesh Kumar', '9876543210', 'rajesh.kumar@fruits.co.in', 'Mumbai - Central Distribution');
INSERT INTO spoc_contacts (name, phone, email, location) VALUES ('Priya Singh', '9876543211', 'priya.singh@delivery.co.in', 'Delhi - Northern Hub');
INSERT INTO spoc_contacts (name, phone, email, location) VALUES ('Amit Patel', '9876543212', 'amit.patel@logistics.co.in', 'Bangalore - IT Hub');
INSERT INTO spoc_contacts (name, phone, email, location) VALUES ('Meera Sharma', '9876543213', 'meera.sharma@supply.co.in', 'Pune - Western Center');
COMMIT;
