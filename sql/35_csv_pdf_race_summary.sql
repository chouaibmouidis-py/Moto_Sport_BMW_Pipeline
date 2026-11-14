-- Preserve CSV participants and attach counts from their paired PDF source version.
-- An absent declared count is never inferred from the observed stop details.

WITH pit_stop_reports AS (
    SELECT DISTINCT source_id, bronze_sha256, pdf_sha256
    FROM silver_pdf_pit_stops
)
SELECT
    classification.*,
    context.championship,
    context.season,
    context.event_id,
    context.session_id,
    pairs.pit_stop_source_id,
    report.bronze_sha256 AS pit_stop_bronze_sha256,
    report.pdf_sha256,
    CAST(NULL AS INTEGER) AS reported_pit_stop_count,
    counts.observed_pit_stop_count,
    summary.valid_duration_count,
    summary.invalid_duration_count,
    summary.average_pit_time_seconds,
    summary.duration_coverage_percent,
    'unavailable_reported_count' AS comparison_status,
    CASE
        WHEN counts.observed_pit_stop_count IS NULL THEN 'no_stop_details'
        ELSE 'available'
    END AS stop_detail_status
FROM silver_classification_csv AS classification
LEFT JOIN source_sessions AS context
    ON classification.source_id = context.source_id
    AND context.document_type = 'classification'
LEFT JOIN classification_pit_stop_sources AS pairs
    ON classification.source_id = pairs.classification_source_id
LEFT JOIN pit_stop_reports AS report
    ON pairs.pit_stop_source_id = report.source_id
LEFT JOIN pit_stop_counts_by_car AS counts
    ON report.source_id = counts.source_id
    AND report.bronze_sha256 = counts.bronze_sha256
    AND classification.car_number = counts.car_number
LEFT JOIN pit_stop_summary AS summary
    ON report.source_id = summary.source_id
    AND report.bronze_sha256 = summary.bronze_sha256
    AND classification.car_number = summary.car_number;
