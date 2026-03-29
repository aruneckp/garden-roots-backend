-- ============================================================
-- Garden Roots - Master Setup Script
-- Database : Oracle 12c+  (XE / XEPDB1 or Cloud ATP/ADB)
-- ============================================================
--
-- USAGE (SQL*Plus or SQLcl):
--
--   LOCAL (XE):
--     sqlplus system/Oracle123@localhost:1521/XEPDB1
--     @run_all.sql
--
--   CLOUD (ATP / Autonomous DB):
--     sqlplus admin/<password>@<wallet_dsn>
--     @run_all.sql
--
--   FRESH INSTALL (drops everything first):
--     @00_drop_all.sql
--     @run_all.sql
--
-- PRE-REQUISITES:
--   • Oracle 12c or later  (XE 18c+ / ATP recommended)
--   • Connected as the application schema owner
--   • User must have CREATE TABLE, CREATE INDEX privileges
--
-- POST-SETUP:
--   • Replace REPLACE_WITH_BCRYPT_HASH in 03_seed_data.sql
--     with a real bcrypt hash BEFORE running in production.
--   • Run 04_verify.sql any time to confirm schema integrity.
-- ============================================================

-- Abort immediately on any error
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

PROMPT
PROMPT ============================================================
PROMPT   Garden Roots - Full Database Setup
PROMPT   Started : &&_DATE  &&_TIME
PROMPT ============================================================

-- ----------------------------------------------------------------
-- STEP 1 : Create all base tables (17 tables)
-- ----------------------------------------------------------------
PROMPT
PROMPT [STEP 1/7] Creating base tables ...
PROMPT
@01_create_tables.sql

-- ----------------------------------------------------------------
-- STEP 2 : Create base indexes
-- ----------------------------------------------------------------
PROMPT
PROMPT [STEP 2/7] Creating indexes ...
PROMPT
@02_create_indexes.sql

-- ----------------------------------------------------------------
-- STEP 3 : Insert seed / bootstrap data
-- ----------------------------------------------------------------
PROMPT
PROMPT [STEP 3/7] Inserting seed data ...
PROMPT
@03_seed_data.sql

-- ----------------------------------------------------------------
-- STEP 4 : Migration 05 - Add USERS table + link orders to users
-- ----------------------------------------------------------------
PROMPT
PROMPT [STEP 4/7] Migration 05 - Adding USERS table ...
PROMPT
@05_add_users.sql

-- ----------------------------------------------------------------
-- STEP 5 : Migration 06 - delivery_type, pickup_location, notes
-- ----------------------------------------------------------------
PROMPT
PROMPT [STEP 5/7] Migration 06 - Delivery type and pickup support ...
PROMPT
@06_order_pickup_and_notes.sql

-- ----------------------------------------------------------------
-- STEP 6 : Migration 07 - delivery_feedback on orders
-- ----------------------------------------------------------------
PROMPT
PROMPT [STEP 6/7] Migration 07 - Delivery feedback column ...
PROMPT
@07_order_delivery_feedback.sql

-- ----------------------------------------------------------------
-- STEP 7 : Migration 08 - shipment_id on orders (reconciliation)
-- ----------------------------------------------------------------
PROMPT
PROMPT [STEP 7/7] Migration 08 - Shipment reconciliation link ...
PROMPT
@08_order_shipment_link.sql

-- ----------------------------------------------------------------
-- DONE
-- ----------------------------------------------------------------
PROMPT
PROMPT ============================================================
PROMPT   Setup complete.  Run @04_verify.sql to confirm.
PROMPT ============================================================
PROMPT
