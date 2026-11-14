-- Extract explicit manufacturer ID/name evidence from loaded JSON Bronze reports.

WITH entries AS (
    SELECT
        document.source_id,
        document.bronze_sha256,
        entry.value
    FROM bronze_classification AS document
    CROSS JOIN json_each(document.classification) AS entry

    UNION ALL

    SELECT
        document.source_id,
        document.bronze_sha256,
        entry.value
    FROM bronze_document AS document
    CROSS JOIN json_each(document.pit_stop_analysis) AS entry
),
cleaned AS (
    SELECT
        source_id,
        bronze_sha256,
        NULLIF(
            TRIM(json_extract_string(value, '$.imsa_manufacturerid')),
            ''
        ) AS manufacturer_source_id,
        NULLIF(
            TRIM(json_extract_string(value, '$.manufacturer')),
            ''
        ) AS manufacturer
    FROM entries
)
SELECT *
FROM cleaned
WHERE manufacturer_source_id IS NOT NULL;