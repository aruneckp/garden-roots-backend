-- ============================================================
-- Garden Roots - Seed / Bootstrap Data
-- Database : Oracle 12c+  (XE / XEPDB1)
-- ============================================================
--
-- IMPORTANT – ADMIN PASSWORD
-- ~~~~~~~~~~~~~~~~~~~~~~~~~~
-- The password hash below is a PLACEHOLDER. Replace it with a
-- real bcrypt hash BEFORE running in any real environment.
--
-- Generate a hash with Python:
--   pip install passlib bcrypt
--   python3 -c "
--     from passlib.context import CryptContext
--     ctx = CryptContext(schemes=['bcrypt'], deprecated='auto')
--     print(ctx.hash('YourStrongPassword'))
--   "
--
-- Then paste the output (e.g. $2b$12$xxxx...) in place of
-- REPLACE_WITH_BCRYPT_HASH below.
-- ============================================================

WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

PROMPT ----------------------------------------------------------
PROMPT  Inserting seed data ...
PROMPT ----------------------------------------------------------

-- ----------------------------------------------------------------
-- Default admin user
-- ----------------------------------------------------------------
MERGE INTO admin_users tgt
USING (SELECT 'admin' AS username FROM dual) src
ON (tgt.username = src.username)
WHEN NOT MATCHED THEN
    INSERT (username, password_hash, full_name, email, role, is_active)
    VALUES (
        'admin',
        'REPLACE_WITH_BCRYPT_HASH',
        'System Administrator',
        'admin@gardenroots.com',
        'admin',
        1
    );

PROMPT   admin_users  -> default admin row inserted (or already exists).

-- ----------------------------------------------------------------
-- Default pickup location (head office / warehouse)
-- ----------------------------------------------------------------
MERGE INTO pickup_locations tgt
USING (SELECT 'Head Office Warehouse' AS name FROM dual) src
ON (tgt.name = src.name)
WHEN NOT MATCHED THEN
    INSERT (name, address, phone, email, manager_name,
            location_type, capacity, current_boxes, is_active, notes)
    VALUES (
        'Head Office Warehouse',
        '123 Garden Street, City, State 00000',
        '+1-000-000-0000',
        'warehouse@gardenroots.com',
        'Warehouse Manager',
        'warehouse',
        500,
        0,
        1,
        'Primary receiving and dispatch warehouse.'
    );

PROMPT   pickup_locations -> Head Office Warehouse inserted (or already exists).

COMMIT;

PROMPT ----------------------------------------------------------
PROMPT  Seed data committed.
PROMPT ----------------------------------------------------------
