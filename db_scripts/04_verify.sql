-- ============================================================
-- Garden Roots - Post-Setup Verification
-- Database : Oracle 12c+  (XE / XEPDB1)
-- Purpose  : Confirms all 17 tables and their indexes exist.
--            Run after run_all.sql to sanity-check the schema.
-- ============================================================

PROMPT ==============================================================
PROMPT  VERIFICATION REPORT
PROMPT ==============================================================

-- ----------------------------------------------------------------
-- 1. Table existence check  (expects 17 rows)
-- ----------------------------------------------------------------
PROMPT
PROMPT [1] Tables found in schema:
PROMPT
SELECT
    table_name,
    CASE WHEN table_name IN (
        'PRODUCTS','LOCATIONS','ADMIN_USERS','SPOC_CONTACTS',
        'PICKUP_LOCATIONS','PRODUCT_VARIANTS','PRICING',
        'STOCK_INVENTORY','ORDERS','SHIPMENTS','ORDER_ITEMS',
        'SHIPMENT_BOXES','DELIVERY_LOGS','SHIPMENT_SUMMARY',
        'PREBOOKINGS','PAYMENT_RECORDS','BOX_ENTRY_LOGS'
    ) THEN 'OK' ELSE 'UNEXPECTED' END AS status
FROM user_tables
WHERE table_name IN (
    'PRODUCTS','LOCATIONS','ADMIN_USERS','SPOC_CONTACTS',
    'PICKUP_LOCATIONS','PRODUCT_VARIANTS','PRICING',
    'STOCK_INVENTORY','ORDERS','SHIPMENTS','ORDER_ITEMS',
    'SHIPMENT_BOXES','DELIVERY_LOGS','SHIPMENT_SUMMARY',
    'PREBOOKINGS','PAYMENT_RECORDS','BOX_ENTRY_LOGS'
)
ORDER BY table_name;

-- ----------------------------------------------------------------
-- 2. Missing tables alert  (expects 0 rows)
-- ----------------------------------------------------------------
PROMPT
PROMPT [2] Missing tables (should be 0 rows):
PROMPT
SELECT expected_table
FROM (
    SELECT 'PRODUCTS'          AS expected_table FROM dual UNION ALL
    SELECT 'LOCATIONS'                           FROM dual UNION ALL
    SELECT 'ADMIN_USERS'                         FROM dual UNION ALL
    SELECT 'SPOC_CONTACTS'                       FROM dual UNION ALL
    SELECT 'PICKUP_LOCATIONS'                    FROM dual UNION ALL
    SELECT 'PRODUCT_VARIANTS'                    FROM dual UNION ALL
    SELECT 'PRICING'                             FROM dual UNION ALL
    SELECT 'STOCK_INVENTORY'                     FROM dual UNION ALL
    SELECT 'ORDERS'                              FROM dual UNION ALL
    SELECT 'SHIPMENTS'                           FROM dual UNION ALL
    SELECT 'ORDER_ITEMS'                         FROM dual UNION ALL
    SELECT 'SHIPMENT_BOXES'                      FROM dual UNION ALL
    SELECT 'DELIVERY_LOGS'                       FROM dual UNION ALL
    SELECT 'SHIPMENT_SUMMARY'                    FROM dual UNION ALL
    SELECT 'PREBOOKINGS'                         FROM dual UNION ALL
    SELECT 'PAYMENT_RECORDS'                     FROM dual UNION ALL
    SELECT 'BOX_ENTRY_LOGS'                      FROM dual
) expected
WHERE expected_table NOT IN (SELECT table_name FROM user_tables);

-- ----------------------------------------------------------------
-- 3. Row counts per table
-- ----------------------------------------------------------------
PROMPT
PROMPT [3] Row counts (seed data):
PROMPT
SELECT 'products'         AS table_name, COUNT(*) AS row_count FROM products         UNION ALL
SELECT 'locations',                      COUNT(*) FROM locations                      UNION ALL
SELECT 'admin_users',                    COUNT(*) FROM admin_users                    UNION ALL
SELECT 'spoc_contacts',                  COUNT(*) FROM spoc_contacts                  UNION ALL
SELECT 'pickup_locations',               COUNT(*) FROM pickup_locations               UNION ALL
SELECT 'product_variants',               COUNT(*) FROM product_variants               UNION ALL
SELECT 'pricing',                        COUNT(*) FROM pricing                        UNION ALL
SELECT 'stock_inventory',                COUNT(*) FROM stock_inventory                UNION ALL
SELECT 'orders',                         COUNT(*) FROM orders                         UNION ALL
SELECT 'shipments',                      COUNT(*) FROM shipments                      UNION ALL
SELECT 'order_items',                    COUNT(*) FROM order_items                    UNION ALL
SELECT 'shipment_boxes',                 COUNT(*) FROM shipment_boxes                 UNION ALL
SELECT 'delivery_logs',                  COUNT(*) FROM delivery_logs                  UNION ALL
SELECT 'shipment_summary',               COUNT(*) FROM shipment_summary               UNION ALL
SELECT 'prebookings',                    COUNT(*) FROM prebookings                    UNION ALL
SELECT 'payment_records',                COUNT(*) FROM payment_records                UNION ALL
SELECT 'box_entry_logs',                 COUNT(*) FROM box_entry_logs
ORDER BY 1;

-- ----------------------------------------------------------------
-- 4. Constraint check  (expects 0 disabled constraints)
-- ----------------------------------------------------------------
PROMPT
PROMPT [4] Disabled constraints (should be 0 rows):
PROMPT
SELECT constraint_name, table_name, constraint_type, status
FROM   user_constraints
WHERE  table_name IN (
    'PRODUCTS','LOCATIONS','ADMIN_USERS','SPOC_CONTACTS',
    'PICKUP_LOCATIONS','PRODUCT_VARIANTS','PRICING',
    'STOCK_INVENTORY','ORDERS','SHIPMENTS','ORDER_ITEMS',
    'SHIPMENT_BOXES','DELIVERY_LOGS','SHIPMENT_SUMMARY',
    'PREBOOKINGS','PAYMENT_RECORDS','BOX_ENTRY_LOGS'
)
AND status != 'ENABLED'
ORDER BY table_name, constraint_name;

-- ----------------------------------------------------------------
-- 5. Index count per table
-- ----------------------------------------------------------------
PROMPT
PROMPT [5] Index count per table:
PROMPT
SELECT table_name, COUNT(*) AS index_count
FROM   user_indexes
WHERE  table_name IN (
    'PRODUCTS','LOCATIONS','ADMIN_USERS','SPOC_CONTACTS',
    'PICKUP_LOCATIONS','PRODUCT_VARIANTS','PRICING',
    'STOCK_INVENTORY','ORDERS','SHIPMENTS','ORDER_ITEMS',
    'SHIPMENT_BOXES','DELIVERY_LOGS','SHIPMENT_SUMMARY',
    'PREBOOKINGS','PAYMENT_RECORDS','BOX_ENTRY_LOGS'
)
GROUP BY table_name
ORDER BY table_name;

-- ----------------------------------------------------------------
-- 6. Seed data sanity check
-- ----------------------------------------------------------------
PROMPT
PROMPT [6] Admin users in system:
PROMPT
SELECT id, username, full_name, email, role, is_active,
       CASE WHEN password_hash = 'REPLACE_WITH_BCRYPT_HASH'
            THEN '*** WARNING: placeholder hash - change before use! ***'
            ELSE 'Hash looks set'
       END AS password_status
FROM   admin_users;

PROMPT
PROMPT ==============================================================
PROMPT  Verification complete. Review results above.
PROMPT ==============================================================
