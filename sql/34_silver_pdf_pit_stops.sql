-- Convert PDF stop durations while preserving provenance and extraction locations.

SELECT
    source_id,
    pdf_sha256,
    bronze_sha256,
    car_number,
    pit_number,
    pit_time_raw,
    ROUND(
        parse_duration_seconds(pit_time_raw),
        3
    ) AS pit_time_in_seconds,
    page_number,
    column_number,
    block_line_number,
    source_line
FROM bronze_pdf_pit_stops;