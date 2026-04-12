-- ============================================================
-- Promo Code Module — Migration Script
-- Run once against your Oracle DB
-- ============================================================

-- 1. Add promo columns to orders table
ALTER TABLE orders ADD promo_code VARCHAR2(50);
ALTER TABLE orders ADD discount_amount NUMBER(10,2) DEFAULT 0;

-- 2. Create promo_codes table
CREATE TABLE promo_codes (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code                 VARCHAR2(50)  NOT NULL UNIQUE,
    promo_type           VARCHAR2(30)  DEFAULT 'global' NOT NULL,
    discount_type        VARCHAR2(20)  DEFAULT 'fixed'  NOT NULL,
    discount_value       NUMBER(10,2)  NOT NULL,
    expiry_date          TIMESTAMP WITH TIME ZONE NOT NULL,
    min_order_amount     NUMBER(10,2)  DEFAULT 0,
    redemption_limit     NUMBER(10,0)  DEFAULT 1  NOT NULL,
    total_used           NUMBER(10,0)  DEFAULT 0  NOT NULL,
    is_active            NUMBER(1,0)   DEFAULT 1  NOT NULL,
    specific_user_id     NUMBER        REFERENCES users(id),
    specific_location_id NUMBER        REFERENCES pickup_locations(id),
    created_at           TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP,
    updated_at           TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP
);

CREATE INDEX idx_promo_codes_active   ON promo_codes(is_active);

-- 3. Create promo_usages table
CREATE TABLE promo_usages (
    id            NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    promo_code_id NUMBER NOT NULL REFERENCES promo_codes(id),
    user_id       NUMBER          REFERENCES users(id),
    order_id      NUMBER NOT NULL REFERENCES orders(id),
    used_at       TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP
);

CREATE INDEX idx_promo_usages_promo ON promo_usages(promo_code_id);
CREATE INDEX idx_promo_usages_user  ON promo_usages(user_id);
CREATE INDEX idx_promo_usages_order ON promo_usages(order_id);
