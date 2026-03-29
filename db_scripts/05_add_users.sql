-- ============================================================================
-- Migration 05: Add customer users table and link orders to users
-- Run this once against the existing schema.
-- ============================================================================

-- 1. Create the users table
CREATE TABLE users (
    id             NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    google_id      VARCHAR2(100) NOT NULL,
    email          VARCHAR2(150) NOT NULL,
    name           VARCHAR2(150),
    picture        VARCHAR2(500),
    phone          VARCHAR2(20),
    whatsapp_phone VARCHAR2(20),
    created_at     TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP,
    updated_at     TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP,
    CONSTRAINT uq_users_google_id UNIQUE (google_id),
    CONSTRAINT uq_users_email     UNIQUE (email)
);

--CREATE INDEX idx_users_google_id ON users (google_id);
--CREATE INDEX idx_users_email     ON users (email);

-- 2. Add user_id foreign key column to orders (nullable — existing orders have no user)
ALTER TABLE orders ADD user_id NUMBER;
ALTER TABLE orders ADD CONSTRAINT fk_orders_user
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL;
CREATE INDEX idx_orders_user_id ON orders (user_id);

COMMIT;
