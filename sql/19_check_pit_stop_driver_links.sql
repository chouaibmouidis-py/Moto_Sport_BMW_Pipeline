-- Identify missing, unmatched or ambiguous incoming and outgoing driver references.

WITH driver_references AS (
    SELECT
        stops.source_id,
        stops.bronze_sha256,
        stops.source_entry_index,
        stops.car_number,
        stops.pit_number,
        reference.driver_role,
        reference.driver_number
    FROM silver_pit_stops AS stops
    CROSS JOIN LATERAL (
        VALUES
            ('in', stops.in_driver_number),
            ('out', stops.out_driver_number)
    ) AS reference(driver_role, driver_number)
),
matched_references AS (
    SELECT
        reference.*,
        (
            SELECT COUNT(*)
            FROM silver_driver_entries AS drivers
            WHERE drivers.source_id = reference.source_id
              AND drivers.bronze_sha256 = reference.bronze_sha256
              AND drivers.source_entry_index = reference.source_entry_index
              AND drivers.driver_number = reference.driver_number
        ) AS match_count
    FROM driver_references AS reference
)
SELECT
    *,
    CASE
        WHEN driver_number IS NULL THEN 'missing'
        WHEN match_count = 0 THEN 'unmatched'
        WHEN match_count > 1 THEN 'ambiguous'
        ELSE 'valid'
    END AS link_status
FROM matched_references
WHERE driver_number IS NULL
   OR match_count != 1;
