-- Compare declared and observed stop counts while preserving every classification entry.

SELECT
    classification.*,
    report.source_id AS pit_stop_source_id,
    report.bronze_sha256 AS pit_stop_bronze_sha256,
    counts.observed_pit_stop_count,
    CASE
        WHEN report.source_id IS NULL
            THEN 'missing_pit_stop_report'

        WHEN classification.reported_pit_stop_count IS NULL
            THEN 'unavailable_reported_count'

        WHEN counts.observed_pit_stop_count IS NULL
            AND classification.reported_pit_stop_count = 0
            THEN 'zero_reported_no_detail'

        WHEN counts.observed_pit_stop_count IS NULL
            THEN 'missing_stop_details'

        WHEN classification.reported_pit_stop_count
            = counts.observed_pit_stop_count
            THEN 'matched'

        ELSE 'count_mismatch'
    END AS comparison_status
FROM silver_classification AS classification
LEFT JOIN classification_pit_stop_sources AS pairs
    ON classification.source_id = pairs.classification_source_id
LEFT JOIN bronze_document AS report
    ON pairs.pit_stop_source_id = report.source_id
LEFT JOIN pit_stop_counts_by_car AS counts
    ON report.source_id = counts.source_id
    AND report.bronze_sha256 = counts.bronze_sha256
    AND classification.car_number = counts.car_number;
