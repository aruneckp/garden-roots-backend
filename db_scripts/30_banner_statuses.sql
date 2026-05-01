-- Seed banner_statuses config key (all known banners enabled by default).
-- Uses MERGE so re-running is safe.
MERGE INTO site_config sc
USING (SELECT 'banner_statuses' AS config_key FROM dual) src
ON (sc.config_key = src.config_key)
WHEN NOT MATCHED THEN
    INSERT (config_key, config_value, description)
    VALUES (
        'banner_statuses',
        '{}',
        'JSON map of banner filename to enabled boolean. Missing keys default to enabled.'
    );
