-- Enrich 2023 participants with evidence-based manufacturer names.
-- Preserve every participant and expose unresolved mappings explicitly.

SELECT
    participant.*,
    reference.manufacturer,
    COALESCE(
        reference.manufacturer_mapping_status,
        'unmapped'
    ) AS manufacturer_mapping_status,
    COALESCE(
        reference.manufacturer_name_count,
        0
    ) AS manufacturer_name_count
FROM csv_pdf_race_summary AS participant
LEFT JOIN manufacturer_reference AS reference
    ON participant.manufacturer_source_id =
       reference.manufacturer_source_id;