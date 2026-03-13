-- ============================================================
-- Garden Roots - Master Setup Script
-- Database : Oracle 12c+  (XE / XEPDB1)
-- ============================================================
--
-- USAGE (SQL*Plus or SQLcl):
--
--   1. Connect to the target schema/user first:
--
--        sqlplus system/Oracle123@localhost:1521/XEPDB1
--        -- or --
--        sql system/Oracle123@localhost:1521/XEPDB1
--
--   2. Run this script from the db_scripts/ directory:
--
--        @run_all.sql
--
--   3. For a FRESH install (drops existing tables first):
--
--        @00_drop_all.sql
--        @run_all.sql
--
-- PRE-REQUISITES:
--   • Oracle 12c or later (XE 18c+ recommended)
--   • Connected as the application schema owner (e.g. system / XEPDB1)
--   • The user must have CREATE TABLE, CREATE INDEX, CREATE SEQUENCE
--     privileges (system user has these by default)
--
-- POST-SETUP:
--   • Open 03_seed_data.sql and replace REPLACE_WITH_BCRYPT_HASH
--     with a real bcrypt hash before running in production.
--   • Run 04_verify.sql any time to confirm schema integrity.
-- ============================================================

-- Abort immediately on any error
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

PROMPT
PROMPT ============================================================
PROMPT   Garden Roots - Database Setup
PROMPT   Started : &&_DATE  &&_TIME
PROMPT ============================================================

-- ----------------------------------------------------------------
-- STEP 1 : Create all tables
-- ----------------------------------------------------------------
PROMPT
PROMPT [STEP 1/3] Creating tables ...
PROMPT
@01_create_tables.sql

-- ----------------------------------------------------------------
-- STEP 2 : Create indexes
-- ----------------------------------------------------------------
PROMPT
PROMPT [STEP 2/3] Creating indexes ...
PROMPT
@02_create_indexes.sql

-- ----------------------------------------------------------------
-- STEP 3 : Insert seed / bootstrap data
-- ----------------------------------------------------------------
PROMPT
PROMPT [STEP 3/3] Inserting seed data ...
PROMPT
@03_seed_data.sql

-- ----------------------------------------------------------------
-- DONE
-- ----------------------------------------------------------------
PROMPT
PROMPT ============================================================
PROMPT   Setup complete.  Run @04_verify.sql to confirm.
PROMPT ============================================================
PROMPT
