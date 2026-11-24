-- Resolve unique manufacturer names and flag ambiguous or unnamed identifiers.
-- Silver values are cleaned; case-only name variants represent one name.
-- MIN retains one deterministic source spelling, without merging different names.

SELECT
    manufacturer_source_id,
    COUNT(DISTINCT lower(manufacturer)) AS manufacturer_name_count,
    CASE
        WHEN COUNT(DISTINCT lower(manufacturer)) = 0 THEN 'unmapped'
        WHEN COUNT(DISTINCT lower(manufacturer)) = 1 THEN 'matched'
        ELSE 'ambiguous'
    END AS manufacturer_mapping_status,
    CASE
        WHEN COUNT(DISTINCT lower(manufacturer)) = 1 THEN MIN(manufacturer)
        ELSE NULL
    END AS manufacturer
FROM manufacturer_reference_input
GROUP BY manufacturer_source_id;