-- Extract explicit manufacturer ID/name evidence from Silver reports.

SELECT
    source_id,
    bronze_sha256,
    manufacturer_source_id,
    manufacturer
FROM
    silver_classification
WHERE
    manufacturer_source_id IS NOT NULL
UNION ALL
SELECT
    source_id,
    bronze_sha256,
    manufacturer_source_id,
    manufacturer
FROM
    silver_car_entries
WHERE
    manufacturer_source_id IS NOT NULL