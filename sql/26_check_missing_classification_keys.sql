-- Count classification entries with missing required key values.

SELECT
    COUNT(*) AS missing_key_count
FROM silver_classification
WHERE source_id IS NULL
    OR bronze_sha256 IS NULL
    OR source_entry_index IS NULL;
