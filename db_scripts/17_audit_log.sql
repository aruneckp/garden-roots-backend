-- ============================================================
-- Migration 17: Audit Logging
-- Creates a single AUDIT_LOG table and row-level triggers
-- on all key tables. The changed_by column is populated from
-- the Oracle CLIENT_IDENTIFIER set by the FastAPI middleware
-- (the logged-in user's email / username from their JWT).
-- ============================================================

-- ------------------------------------------------------------
-- AUDIT_LOG table
-- ------------------------------------------------------------
CREATE TABLE audit_log (
    id          NUMBER GENERATED ALWAYS AS IDENTITY NOT NULL,
    table_name  VARCHAR2(100)              NOT NULL,
    operation   VARCHAR2(10)               NOT NULL,   -- INSERT / UPDATE / DELETE
    record_id   NUMBER,
    changed_by  VARCHAR2(200),                         -- app user (email or username)
    changed_at  TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    old_values  CLOB,                                  -- JSON of previous values
    new_values  CLOB,                                  -- JSON of new / changed values
    CONSTRAINT pk_audit_log PRIMARY KEY (id),
    CONSTRAINT chk_audit_op CHECK (operation IN ('INSERT','UPDATE','DELETE'))
);

CREATE INDEX idx_audit_table  ON audit_log (table_name);
CREATE INDEX idx_audit_record ON audit_log (table_name, record_id);
CREATE INDEX idx_audit_user   ON audit_log (changed_by);
CREATE INDEX idx_audit_at     ON audit_log (changed_at);

COMMENT ON TABLE  audit_log             IS 'Application-level audit trail for all key table changes';
COMMENT ON COLUMN audit_log.changed_by  IS 'Logged-in app user (email/username) from JWT, set via DBMS_SESSION.SET_IDENTIFIER';
COMMENT ON COLUMN audit_log.old_values  IS 'JSON object of column values before the change';
COMMENT ON COLUMN audit_log.new_values  IS 'JSON object of column values after the change';

COMMIT;

-- ============================================================
-- Helper: get app user from CLIENT_IDENTIFIER, fall back to DB user
-- ============================================================
-- Used inside every trigger:
--   v_user := NVL(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'), SYS_CONTEXT('USERENV','SESSION_USER'));

-- ============================================================
-- TRIGGER: PRODUCTS
-- ============================================================
CREATE OR REPLACE TRIGGER trg_products_audit
AFTER INSERT OR UPDATE OR DELETE ON products
FOR EACH ROW
DECLARE
    v_op     VARCHAR2(10);
    v_id     NUMBER;
    v_user   VARCHAR2(200);
    v_old    CLOB := '';
    v_new    CLOB := '';
BEGIN
    v_user := NVL(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'), SYS_CONTEXT('USERENV','SESSION_USER'));

    IF INSERTING THEN
        v_op := 'INSERT';  v_id := :NEW.id;
        v_new := '{"name":"'||:NEW.name||'","tag":"'||NVL(:NEW.tag,'')||'","is_active":'||NVL(:NEW.is_active,1)||',"origin":"'||NVL(:NEW.origin,'')||'"}';
    ELSIF DELETING THEN
        v_op := 'DELETE';  v_id := :OLD.id;
        v_old := '{"name":"'||:OLD.name||'","is_active":'||NVL(:OLD.is_active,1)||'}';
    ELSE
        v_op := 'UPDATE';  v_id := :NEW.id;
        IF NVL(:OLD.name,'~') != NVL(:NEW.name,'~') THEN
            v_old := v_old||'"name":"'||NVL(:OLD.name,'')||'",';
            v_new := v_new||'"name":"'||NVL(:NEW.name,'')||'",';
        END IF;
        IF NVL(:OLD.description,'~') != NVL(:NEW.description,'~') THEN
            v_old := v_old||'"description":"'||NVL(:OLD.description,'')||'",';
            v_new := v_new||'"description":"'||NVL(:NEW.description,'')||'",';
        END IF;
        IF NVL(:OLD.origin,'~') != NVL(:NEW.origin,'~') THEN
            v_old := v_old||'"origin":"'||NVL(:OLD.origin,'')||'",';
            v_new := v_new||'"origin":"'||NVL(:NEW.origin,'')||'",';
        END IF;
        IF NVL(:OLD.tag,'~') != NVL(:NEW.tag,'~') THEN
            v_old := v_old||'"tag":"'||NVL(:OLD.tag,'')||'",';
            v_new := v_new||'"tag":"'||NVL(:NEW.tag,'')||'",';
        END IF;
        IF NVL(:OLD.is_active,-1) != NVL(:NEW.is_active,-1) THEN
            v_old := v_old||'"is_active":'||NVL(TO_CHAR(:OLD.is_active),'null')||',';
            v_new := v_new||'"is_active":'||NVL(TO_CHAR(:NEW.is_active),'null')||',';
        END IF;
        IF NVL(:OLD.season_start,'~') != NVL(:NEW.season_start,'~') THEN
            v_old := v_old||'"season_start":"'||NVL(:OLD.season_start,'')||'",';
            v_new := v_new||'"season_start":"'||NVL(:NEW.season_start,'')||'",';
        END IF;
        IF NVL(:OLD.season_end,'~') != NVL(:NEW.season_end,'~') THEN
            v_old := v_old||'"season_end":"'||NVL(:OLD.season_end,'')||'",';
            v_new := v_new||'"season_end":"'||NVL(:NEW.season_end,'')||'",';
        END IF;
        IF LENGTH(v_old) > 0 THEN
            v_old := '{'||RTRIM(v_old,',')||'}';
            v_new := '{'||RTRIM(v_new,',')||'}';
        END IF;
    END IF;

    IF v_op = 'UPDATE' AND LENGTH(v_old) = 0 THEN RETURN; END IF;

    INSERT INTO audit_log (table_name, operation, record_id, changed_by, old_values, new_values)
    VALUES ('PRODUCTS', v_op, v_id, v_user, v_old, v_new);
END;
/

-- ============================================================
-- TRIGGER: PRODUCT_VARIANTS
-- ============================================================
CREATE OR REPLACE TRIGGER trg_product_variants_audit
AFTER INSERT OR UPDATE OR DELETE ON product_variants
FOR EACH ROW
DECLARE
    v_op   VARCHAR2(10);
    v_id   NUMBER;
    v_user VARCHAR2(200);
    v_old  CLOB := '';
    v_new  CLOB := '';
BEGIN
    v_user := NVL(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'), SYS_CONTEXT('USERENV','SESSION_USER'));

    IF INSERTING THEN
        v_op := 'INSERT';  v_id := :NEW.id;
        v_new := '{"product_id":'||:NEW.product_id||',"size_name":"'||:NEW.size_name||'","unit":"'||:NEW.unit||'"}';
    ELSIF DELETING THEN
        v_op := 'DELETE';  v_id := :OLD.id;
        v_old := '{"product_id":'||:OLD.product_id||',"size_name":"'||:OLD.size_name||'"}';
    ELSE
        v_op := 'UPDATE';  v_id := :NEW.id;
        IF NVL(:OLD.size_name,'~') != NVL(:NEW.size_name,'~') THEN
            v_old := v_old||'"size_name":"'||NVL(:OLD.size_name,'')||'",';
            v_new := v_new||'"size_name":"'||NVL(:NEW.size_name,'')||'",';
        END IF;
        IF NVL(:OLD.unit,'~') != NVL(:NEW.unit,'~') THEN
            v_old := v_old||'"unit":"'||NVL(:OLD.unit,'')||'",';
            v_new := v_new||'"unit":"'||NVL(:NEW.unit,'')||'",';
        END IF;
        IF NVL(TO_CHAR(:OLD.box_weight),'~') != NVL(TO_CHAR(:NEW.box_weight),'~') THEN
            v_old := v_old||'"box_weight":'||NVL(TO_CHAR(:OLD.box_weight),'null')||',';
            v_new := v_new||'"box_weight":'||NVL(TO_CHAR(:NEW.box_weight),'null')||',';
        END IF;
        IF LENGTH(v_old) > 0 THEN
            v_old := '{'||RTRIM(v_old,',')||'}';
            v_new := '{'||RTRIM(v_new,',')||'}';
        END IF;
    END IF;

    IF v_op = 'UPDATE' AND LENGTH(v_old) = 0 THEN RETURN; END IF;

    INSERT INTO audit_log (table_name, operation, record_id, changed_by, old_values, new_values)
    VALUES ('PRODUCT_VARIANTS', v_op, v_id, v_user, v_old, v_new);
END;
/

-- ============================================================
-- TRIGGER: PRICING
-- ============================================================
CREATE OR REPLACE TRIGGER trg_pricing_audit
AFTER INSERT OR UPDATE OR DELETE ON pricing
FOR EACH ROW
DECLARE
    v_op   VARCHAR2(10);
    v_id   NUMBER;
    v_user VARCHAR2(200);
    v_old  CLOB := '';
    v_new  CLOB := '';
BEGIN
    v_user := NVL(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'), SYS_CONTEXT('USERENV','SESSION_USER'));

    IF INSERTING THEN
        v_op := 'INSERT';  v_id := :NEW.id;
        v_new := '{"product_variant_id":'||:NEW.product_variant_id||',"base_price":'||:NEW.base_price||',"currency":"'||:NEW.currency||'"}';
    ELSIF DELETING THEN
        v_op := 'DELETE';  v_id := :OLD.id;
        v_old := '{"base_price":'||:OLD.base_price||',"currency":"'||:OLD.currency||'"}';
    ELSE
        v_op := 'UPDATE';  v_id := :NEW.id;
        IF NVL(TO_CHAR(:OLD.base_price),'~') != NVL(TO_CHAR(:NEW.base_price),'~') THEN
            v_old := v_old||'"base_price":'||NVL(TO_CHAR(:OLD.base_price),'null')||',';
            v_new := v_new||'"base_price":'||NVL(TO_CHAR(:NEW.base_price),'null')||',';
        END IF;
        IF NVL(:OLD.currency,'~') != NVL(:NEW.currency,'~') THEN
            v_old := v_old||'"currency":"'||NVL(:OLD.currency,'')||'",';
            v_new := v_new||'"currency":"'||NVL(:NEW.currency,'')||'",';
        END IF;
        IF NVL(TO_CHAR(:OLD.valid_from,'YYYY-MM-DD'),'~') != NVL(TO_CHAR(:NEW.valid_from,'YYYY-MM-DD'),'~') THEN
            v_old := v_old||'"valid_from":"'||NVL(TO_CHAR(:OLD.valid_from,'YYYY-MM-DD'),'')||'",';
            v_new := v_new||'"valid_from":"'||NVL(TO_CHAR(:NEW.valid_from,'YYYY-MM-DD'),'')||'",';
        END IF;
        IF NVL(TO_CHAR(:OLD.valid_to,'YYYY-MM-DD'),'~') != NVL(TO_CHAR(:NEW.valid_to,'YYYY-MM-DD'),'~') THEN
            v_old := v_old||'"valid_to":"'||NVL(TO_CHAR(:OLD.valid_to,'YYYY-MM-DD'),'')||'",';
            v_new := v_new||'"valid_to":"'||NVL(TO_CHAR(:NEW.valid_to,'YYYY-MM-DD'),'')||'",';
        END IF;
        IF LENGTH(v_old) > 0 THEN
            v_old := '{'||RTRIM(v_old,',')||'}';
            v_new := '{'||RTRIM(v_new,',')||'}';
        END IF;
    END IF;

    IF v_op = 'UPDATE' AND LENGTH(v_old) = 0 THEN RETURN; END IF;

    INSERT INTO audit_log (table_name, operation, record_id, changed_by, old_values, new_values)
    VALUES ('PRICING', v_op, v_id, v_user, v_old, v_new);
END;
/

-- ============================================================
-- TRIGGER: ORDERS
-- ============================================================
CREATE OR REPLACE TRIGGER trg_orders_audit
AFTER INSERT OR UPDATE OR DELETE ON orders
FOR EACH ROW
DECLARE
    v_op   VARCHAR2(10);
    v_id   NUMBER;
    v_user VARCHAR2(200);
    v_old  CLOB := '';
    v_new  CLOB := '';
BEGIN
    v_user := NVL(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'), SYS_CONTEXT('USERENV','SESSION_USER'));

    IF INSERTING THEN
        v_op := 'INSERT';  v_id := :NEW.id;
        v_new := '{"order_ref":"'||NVL(:NEW.order_ref,'')||'","order_status":"'||NVL(:NEW.order_status,'')||'","payment_status":"'||NVL(:NEW.payment_status,'')||'","customer_email":"'||NVL(:NEW.customer_email,'')||'"}';
    ELSIF DELETING THEN
        v_op := 'DELETE';  v_id := :OLD.id;
        v_old := '{"order_ref":"'||NVL(:OLD.order_ref,'')||'","order_status":"'||NVL(:OLD.order_status,'')||'"}';
    ELSE
        v_op := 'UPDATE';  v_id := :NEW.id;
        IF NVL(:OLD.order_status,'~') != NVL(:NEW.order_status,'~') THEN
            v_old := v_old||'"order_status":"'||NVL(:OLD.order_status,'')||'",';
            v_new := v_new||'"order_status":"'||NVL(:NEW.order_status,'')||'",';
        END IF;
        IF NVL(:OLD.payment_status,'~') != NVL(:NEW.payment_status,'~') THEN
            v_old := v_old||'"payment_status":"'||NVL(:OLD.payment_status,'')||'",';
            v_new := v_new||'"payment_status":"'||NVL(:NEW.payment_status,'')||'",';
        END IF;
        IF NVL(:OLD.customer_name,'~') != NVL(:NEW.customer_name,'~') THEN
            v_old := v_old||'"customer_name":"'||NVL(:OLD.customer_name,'')||'",';
            v_new := v_new||'"customer_name":"'||NVL(:NEW.customer_name,'')||'",';
        END IF;
        IF NVL(:OLD.customer_email,'~') != NVL(:NEW.customer_email,'~') THEN
            v_old := v_old||'"customer_email":"'||NVL(:OLD.customer_email,'')||'",';
            v_new := v_new||'"customer_email":"'||NVL(:NEW.customer_email,'')||'",';
        END IF;
        IF NVL(:OLD.customer_phone,'~') != NVL(:NEW.customer_phone,'~') THEN
            v_old := v_old||'"customer_phone":"'||NVL(:OLD.customer_phone,'')||'",';
            v_new := v_new||'"customer_phone":"'||NVL(:NEW.customer_phone,'')||'",';
        END IF;
        IF NVL(:OLD.delivery_address,'~') != NVL(:NEW.delivery_address,'~') THEN
            v_old := v_old||'"delivery_address":"'||NVL(:OLD.delivery_address,'')||'",';
            v_new := v_new||'"delivery_address":"'||NVL(:NEW.delivery_address,'')||'",';
        END IF;
        IF NVL(TO_CHAR(:OLD.total_price),'~') != NVL(TO_CHAR(:NEW.total_price),'~') THEN
            v_old := v_old||'"total_price":'||NVL(TO_CHAR(:OLD.total_price),'null')||',';
            v_new := v_new||'"total_price":'||NVL(TO_CHAR(:NEW.total_price),'null')||',';
        END IF;
        IF LENGTH(v_old) > 0 THEN
            v_old := '{'||RTRIM(v_old,',')||'}';
            v_new := '{'||RTRIM(v_new,',')||'}';
        END IF;
    END IF;

    IF v_op = 'UPDATE' AND LENGTH(v_old) = 0 THEN RETURN; END IF;

    INSERT INTO audit_log (table_name, operation, record_id, changed_by, old_values, new_values)
    VALUES ('ORDERS', v_op, v_id, v_user, v_old, v_new);
END;
/

-- ============================================================
-- TRIGGER: SITE_CONFIG
-- ============================================================
CREATE OR REPLACE TRIGGER trg_site_config_audit
AFTER INSERT OR UPDATE OR DELETE ON site_config
FOR EACH ROW
DECLARE
    v_op   VARCHAR2(10);
    v_id   NUMBER;
    v_user VARCHAR2(200);
    v_old  CLOB := '';
    v_new  CLOB := '';
BEGIN
    v_user := NVL(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'), SYS_CONTEXT('USERENV','SESSION_USER'));

    IF INSERTING THEN
        v_op := 'INSERT';  v_id := :NEW.id;
        v_new := '{"config_key":"'||NVL(:NEW.config_key,'')||'","config_value":"'||NVL(:NEW.config_value,'')||'"}';
    ELSIF DELETING THEN
        v_op := 'DELETE';  v_id := :OLD.id;
        v_old := '{"config_key":"'||NVL(:OLD.config_key,'')||'","config_value":"'||NVL(:OLD.config_value,'')||'"}';
    ELSE
        v_op := 'UPDATE';  v_id := :NEW.id;
        IF NVL(:OLD.config_value,'~') != NVL(:NEW.config_value,'~') THEN
            v_old := v_old||'"config_key":"'||NVL(:OLD.config_key,'')||'","config_value":"'||NVL(:OLD.config_value,'')||'",';
            v_new := v_new||'"config_key":"'||NVL(:NEW.config_key,'')||'","config_value":"'||NVL(:NEW.config_value,'')||'",';
        END IF;
        IF LENGTH(v_old) > 0 THEN
            v_old := '{'||RTRIM(v_old,',')||'}';
            v_new := '{'||RTRIM(v_new,',')||'}';
        END IF;
    END IF;

    IF v_op = 'UPDATE' AND LENGTH(v_old) = 0 THEN RETURN; END IF;

    INSERT INTO audit_log (table_name, operation, record_id, changed_by, old_values, new_values)
    VALUES ('SITE_CONFIG', v_op, v_id, v_user, v_old, v_new);
END;
/

-- ============================================================
-- TRIGGER: PROMO_CODES
-- ============================================================
CREATE OR REPLACE TRIGGER trg_promo_codes_audit
AFTER INSERT OR UPDATE OR DELETE ON promo_codes
FOR EACH ROW
DECLARE
    v_op   VARCHAR2(10);
    v_id   NUMBER;
    v_user VARCHAR2(200);
    v_old  CLOB := '';
    v_new  CLOB := '';
BEGIN
    v_user := NVL(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'), SYS_CONTEXT('USERENV','SESSION_USER'));

    IF INSERTING THEN
        v_op := 'INSERT';  v_id := :NEW.id;
        v_new := '{"code":"'||NVL(:NEW.code,'')||'","discount_type":"'||NVL(:NEW.discount_type,'')||'","discount_value":'||NVL(:NEW.discount_value,0)||',"is_active":'||NVL(:NEW.is_active,1)||'}';
    ELSIF DELETING THEN
        v_op := 'DELETE';  v_id := :OLD.id;
        v_old := '{"code":"'||NVL(:OLD.code,'')||'"}';
    ELSE
        v_op := 'UPDATE';  v_id := :NEW.id;
        IF NVL(:OLD.code,'~') != NVL(:NEW.code,'~') THEN
            v_old := v_old||'"code":"'||NVL(:OLD.code,'')||'",';
            v_new := v_new||'"code":"'||NVL(:NEW.code,'')||'",';
        END IF;
        IF NVL(TO_CHAR(:OLD.discount_value),'~') != NVL(TO_CHAR(:NEW.discount_value),'~') THEN
            v_old := v_old||'"discount_value":'||NVL(TO_CHAR(:OLD.discount_value),'null')||',';
            v_new := v_new||'"discount_value":'||NVL(TO_CHAR(:NEW.discount_value),'null')||',';
        END IF;
        IF NVL(:OLD.discount_type,'~') != NVL(:NEW.discount_type,'~') THEN
            v_old := v_old||'"discount_type":"'||NVL(:OLD.discount_type,'')||'",';
            v_new := v_new||'"discount_type":"'||NVL(:NEW.discount_type,'')||'",';
        END IF;
        IF NVL(:OLD.is_active,-1) != NVL(:NEW.is_active,-1) THEN
            v_old := v_old||'"is_active":'||NVL(TO_CHAR(:OLD.is_active),'null')||',';
            v_new := v_new||'"is_active":'||NVL(TO_CHAR(:NEW.is_active),'null')||',';
        END IF;
        IF LENGTH(v_old) > 0 THEN
            v_old := '{'||RTRIM(v_old,',')||'}';
            v_new := '{'||RTRIM(v_new,',')||'}';
        END IF;
    END IF;

    IF v_op = 'UPDATE' AND LENGTH(v_old) = 0 THEN RETURN; END IF;

    INSERT INTO audit_log (table_name, operation, record_id, changed_by, old_values, new_values)
    VALUES ('PROMO_CODES', v_op, v_id, v_user, v_old, v_new);
END;
/

-- ============================================================
-- TRIGGER: PICKUP_LOCATIONS
-- ============================================================
CREATE OR REPLACE TRIGGER trg_pickup_locations_audit
AFTER INSERT OR UPDATE OR DELETE ON pickup_locations
FOR EACH ROW
DECLARE
    v_op   VARCHAR2(10);
    v_id   NUMBER;
    v_user VARCHAR2(200);
    v_old  CLOB := '';
    v_new  CLOB := '';
BEGIN
    v_user := NVL(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'), SYS_CONTEXT('USERENV','SESSION_USER'));

    IF INSERTING THEN
        v_op := 'INSERT';  v_id := :NEW.id;
        v_new := '{"name":"'||NVL(:NEW.name,'')||'","address":"'||NVL(:NEW.address,'')||'","is_active":'||NVL(:NEW.is_active,1)||'}';
    ELSIF DELETING THEN
        v_op := 'DELETE';  v_id := :OLD.id;
        v_old := '{"name":"'||NVL(:OLD.name,'')||'"}';
    ELSE
        v_op := 'UPDATE';  v_id := :NEW.id;
        IF NVL(:OLD.name,'~') != NVL(:NEW.name,'~') THEN
            v_old := v_old||'"name":"'||NVL(:OLD.name,'')||'",';
            v_new := v_new||'"name":"'||NVL(:NEW.name,'')||'",';
        END IF;
        IF NVL(:OLD.address,'~') != NVL(:NEW.address,'~') THEN
            v_old := v_old||'"address":"'||NVL(:OLD.address,'')||'",';
            v_new := v_new||'"address":"'||NVL(:NEW.address,'')||'",';
        END IF;
        IF NVL(:OLD.is_active,-1) != NVL(:NEW.is_active,-1) THEN
            v_old := v_old||'"is_active":'||NVL(TO_CHAR(:OLD.is_active),'null')||',';
            v_new := v_new||'"is_active":'||NVL(TO_CHAR(:NEW.is_active),'null')||',';
        END IF;
        IF LENGTH(v_old) > 0 THEN
            v_old := '{'||RTRIM(v_old,',')||'}';
            v_new := '{'||RTRIM(v_new,',')||'}';
        END IF;
    END IF;

    IF v_op = 'UPDATE' AND LENGTH(v_old) = 0 THEN RETURN; END IF;

    INSERT INTO audit_log (table_name, operation, record_id, changed_by, old_values, new_values)
    VALUES ('PICKUP_LOCATIONS', v_op, v_id, v_user, v_old, v_new);
END;
/

-- ============================================================
-- TRIGGER: SHIPMENTS
-- ============================================================
CREATE OR REPLACE TRIGGER trg_shipments_audit
AFTER INSERT OR UPDATE OR DELETE ON shipments
FOR EACH ROW
DECLARE
    v_op   VARCHAR2(10);
    v_id   NUMBER;
    v_user VARCHAR2(200);
    v_old  CLOB := '';
    v_new  CLOB := '';
BEGIN
    v_user := NVL(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'), SYS_CONTEXT('USERENV','SESSION_USER'));

    IF INSERTING THEN
        v_op := 'INSERT';  v_id := :NEW.id;
        v_new := '{"shipment_ref":"'||NVL(:NEW.shipment_ref,'')||'","status":"'||NVL(:NEW.status,'')||'"}';
    ELSIF DELETING THEN
        v_op := 'DELETE';  v_id := :OLD.id;
        v_old := '{"shipment_ref":"'||NVL(:OLD.shipment_ref,'')||'","status":"'||NVL(:OLD.status,'')||'"}';
    ELSE
        v_op := 'UPDATE';  v_id := :NEW.id;
        IF NVL(:OLD.status,'~') != NVL(:NEW.status,'~') THEN
            v_old := v_old||'"status":"'||NVL(:OLD.status,'')||'",';
            v_new := v_new||'"status":"'||NVL(:NEW.status,'')||'",';
        END IF;
        IF NVL(TO_CHAR(:OLD.arrival_date,'YYYY-MM-DD'),'~') != NVL(TO_CHAR(:NEW.arrival_date,'YYYY-MM-DD'),'~') THEN
            v_old := v_old||'"arrival_date":"'||NVL(TO_CHAR(:OLD.arrival_date,'YYYY-MM-DD'),'')||'",';
            v_new := v_new||'"arrival_date":"'||NVL(TO_CHAR(:NEW.arrival_date,'YYYY-MM-DD'),'')||'",';
        END IF;
        IF LENGTH(v_old) > 0 THEN
            v_old := '{'||RTRIM(v_old,',')||'}';
            v_new := '{'||RTRIM(v_new,',')||'}';
        END IF;
    END IF;

    IF v_op = 'UPDATE' AND LENGTH(v_old) = 0 THEN RETURN; END IF;

    INSERT INTO audit_log (table_name, operation, record_id, changed_by, old_values, new_values)
    VALUES ('SHIPMENTS', v_op, v_id, v_user, v_old, v_new);
END;
/

COMMIT;
