SELECT
    source_id,
    bronze_sha256,
    COUNT(*) AS participant_count,
    COUNT(*) FILTER (
        WHERE comparison_status = 'count_mismatch'
    ) AS count_mismatch_count,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE comparison_status = 'count_mismatch'
        ) / COUNT(*),
        2
    ) AS count_mismatch_percent
FROM race_car_summary
GROUP BY source_id, bronze_sha256;