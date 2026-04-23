-- ============================================================
-- Migration 22: Add price and is_active to delivery_tags
-- ============================================================

--PROMPT ----------------------------------------------------------
--PROMPT  [22-1] Adding price column to DELIVERY_TAGS
--PROMPT ----------------------------------------------------------
ALTER TABLE delivery_tags ADD price NUMBER(10,2) DEFAULT NULL;

--PROMPT ----------------------------------------------------------
--PROMPT  [22-2] Adding is_active flag to DELIVERY_TAGS
--PROMPT ----------------------------------------------------------
ALTER TABLE delivery_tags ADD is_active NUMBER(1) DEFAULT 1 NOT NULL;

--PROMPT ----------------------------------------------------------
--PROMPT  [22] Migration complete.
--PROMPT ----------------------------------------------------------
