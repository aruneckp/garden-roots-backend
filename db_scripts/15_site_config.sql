-- ============================================================
-- Migration 15: Central site configuration table
-- Stores key/value pairs for site-wide settings.
-- banner_messages: pipe-separated list of topbar messages
-- ============================================================

--PROMPT ----------------------------------------------------------
--PROMPT  [15-1] Creating table: SITE_CONFIG
--PROMPT ----------------------------------------------------------
CREATE TABLE site_config (
    id           NUMBER GENERATED ALWAYS AS IDENTITY NOT NULL,
    config_key   VARCHAR2(100)  NOT NULL,
    config_value VARCHAR2(2000),
    description  VARCHAR2(300),
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP,
    CONSTRAINT pk_site_config     PRIMARY KEY (id),
    CONSTRAINT uq_site_config_key UNIQUE (config_key)
);

--PROMPT ----------------------------------------------------------
--PROMPT  [15-2] Seed default banner messages (pipe-separated)
--PROMPT ----------------------------------------------------------
INSERT INTO site_config (config_key, config_value, description)
VALUES (
    'banner_messages',
    '🥭 Fresh Indian Mangoes Air-Flown to Singapore — Free delivery over $150|🚚 Order before 2pm for same-day dispatch — delivered in 24–48 hrs|✨ Season 2026 — Premium varieties from India''s finest orchards|SEASON OPENIGN SOON',
    'Pipe-separated list of topbar banner messages shown in rotation'
);

COMMIT;
