-- ============================================================
-- Migration 12: Role-Based Authentication
-- Adds role + delivery_boy_id to the users table.
-- Roles: customer (default), admin, delivery
-- Run AFTER 09_delivery_boy_module.sql (delivery_boys table must exist).
-- ============================================================

--PROMPT ----------------------------------------------------------
--PROMPT  [12-1] Adding ROLE column to USERS
--PROMPT ----------------------------------------------------------
ALTER TABLE users ADD role VARCHAR2(20) DEFAULT 'customer' NOT NULL;

--PROMPT ----------------------------------------------------------
--PROMPT  [12-2] Adding DELIVERY_BOY_ID FK to USERS
--PROMPT   (links a delivery-role user to their delivery_boys row)
--PROMPT ----------------------------------------------------------
ALTER TABLE users ADD delivery_boy_id NUMBER;

ALTER TABLE users ADD CONSTRAINT fk_users_delivery_boy
    FOREIGN KEY (delivery_boy_id) REFERENCES delivery_boys (id);

CREATE INDEX idx_users_role           ON users (role);
CREATE INDEX idx_users_delivery_boy   ON users (delivery_boy_id);

--PROMPT ----------------------------------------------------------
--PROMPT  [12-3] Usage examples (run manually as needed)
--PROMPT ----------------------------------------------------------
-- Set a user as admin:
--   UPDATE users SET role = 'admin' WHERE email = 'you@example.com';
--
-- Set a user as delivery (must have a delivery_boys row first):
--   UPDATE users SET role = 'delivery', delivery_boy_id = <id>
--     WHERE email = 'driver@example.com';
--
-- Revert to customer:
--   UPDATE users SET role = 'customer', delivery_boy_id = NULL
--     WHERE email = 'someone@example.com';

COMMIT;
