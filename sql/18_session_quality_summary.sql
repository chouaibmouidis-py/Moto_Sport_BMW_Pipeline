-- Summarize session field quality by source, Bronze version and field.

WITH field_statuses AS (
    SELECT
        sessions.source_id,
        sessions.bronze_sha256,
        quality.field_name,
        quality.status
    FROM silver_sessions AS sessions
    CROSS JOIN LATERAL (
        VALUES
            ('air_temperature', sessions.air_temperature_status),
            ('track_temperature', sessions.track_temperature_status),
            ('session_datetime', sessions.session_datetime_status),
            (
                'report_creation_datetime',
                sessions.report_creation_datetime_status
            )
    ) AS quality(field_name, status)
)
SELECT
    source_id,
    bronze_sha256,
    field_name,
    COUNT(*) AS checked_count,
    COUNT(*) FILTER (WHERE status = 'valid') AS valid_count,
    COUNT(*) FILTER (WHERE status = 'missing') AS missing_count,
    COUNT(*) FILTER (WHERE status = 'invalid') AS invalid_count
FROM field_statuses
GROUP BY source_id, bronze_sha256, field_name
ORDER BY source_id, bronze_sha256, field_name;
