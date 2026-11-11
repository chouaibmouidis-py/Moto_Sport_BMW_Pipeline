SELECT
    classification.source_id AS classification_source_id,
    pits.source_id AS pit_stop_source_id
FROM source_sessions AS classification
JOIN source_sessions AS pits
    ON classification.championship = pits.championship
    AND classification.season = pits.season
    AND classification.event_id = pits.event_id
    AND classification.session_id = pits.session_id
WHERE classification.document_type = 'classification'
    AND pits.document_type = 'pit_stops';