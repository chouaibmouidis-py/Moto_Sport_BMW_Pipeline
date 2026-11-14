-- Resolve unique manufacturer names and flag ambiguous or unnamed identifiers.
-- Input values must be cleaned; absent identifiers are handled by the caller.

SELECT
    manufacturer_source_id,
    COUNT(DISTINCT manufacturer) AS manufacturer_name_count,
    CASE
        WHEN COUNT(DISTINCT manufacturer) = 0 THEN 'unmapped'
        WHEN COUNT(DISTINCT manufacturer) = 1 THEN 'matched'
        ELSE 'ambiguous'
    END AS manufacturer_mapping_status,
    CASE
        WHEN COUNT(DISTINCT manufacturer) = 1 THEN MIN(manufacturer)
        ELSE NULL
    END AS manufacturer
FROM manufacturer_reference_input
GROUP BY manufacturer_source_id;