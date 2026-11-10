WITH duplicate_keys AS (
    SELECT
        source_id,
        bronze_sha256
    FROM silver_sessions
    GROUP BY source_id, bronze_sha256
    HAVING COUNT(*) > 1
)
SELECT
    (
        SELECT COUNT(*)
        FROM silver_sessions
        WHERE source_id IS NULL
           OR bronze_sha256 IS NULL
    ) AS missing_key_count,
    (
        SELECT COUNT(*)
        FROM duplicate_keys
    ) AS duplicate_key_count;