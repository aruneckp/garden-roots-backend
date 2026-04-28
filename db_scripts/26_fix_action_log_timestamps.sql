-- Migration 26: Fix TIMESTAMP WITH TIME ZONE columns on action log tables
--
-- python-oracledb thin mode (DPY-3022) cannot handle named timezones stored
-- in TIMESTAMP WITH TIME ZONE columns.  The seed INSERT statements in migration 25
-- used DEFAULT CURRENT_TIMESTAMP, which captured the DB session timezone
-- (e.g. Asia/Singapore — a named zone).  This migration converts all existing
-- rows to UTC offset (+00:00) and changes both table defaults so future rows
-- are always stored with a numeric UTC offset that thin mode can read.

-- ── Fix existing seed rows in order_action_types ─────────────────────────────
UPDATE order_action_types
   SET created_at = FROM_TZ(SYS_EXTRACT_UTC(created_at), '+00:00');

-- ── Change column defaults to UTC offset ─────────────────────────────────────
ALTER TABLE order_action_types
    MODIFY created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP AT TIME ZONE 'UTC';

ALTER TABLE order_action_logs
    MODIFY created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP AT TIME ZONE 'UTC';

COMMIT;
