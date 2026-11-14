-- Enrich participants with declared session context and versioned stop statistics.

SELECT
    classification.*,
    context.championship,
    context.season,
    context.event_id,
    context.session_id,
    summary.valid_duration_count,
    summary.invalid_duration_count,
    summary.average_pit_time_seconds,
    summary.duration_coverage_percent
FROM classification_pit_stop_comparison AS classification
LEFT JOIN source_sessions AS context
    ON classification.source_id = context.source_id
    AND context.document_type = 'classification'
LEFT JOIN pit_stop_summary AS summary
    ON classification.pit_stop_source_id = summary.source_id
    AND classification.pit_stop_bronze_sha256 = summary.bronze_sha256
    AND classification.car_number = summary.car_number;