SELECT
    stops.*,
    incoming.first_name AS in_driver_first_name,
    incoming.surname AS in_driver_surname,
    outgoing.first_name AS out_driver_first_name,
    outgoing.surname AS out_driver_surname
FROM silver_pit_stops AS stops
LEFT JOIN silver_driver_entries AS incoming
    ON stops.source_id = incoming.source_id
   AND stops.bronze_sha256 = incoming.bronze_sha256
   AND stops.source_entry_index = incoming.source_entry_index
   AND stops.in_driver_number = incoming.driver_number
LEFT JOIN silver_driver_entries AS outgoing
    ON stops.source_id = outgoing.source_id
   AND stops.bronze_sha256 = outgoing.bronze_sha256
   AND stops.source_entry_index = outgoing.source_entry_index
   AND stops.out_driver_number = outgoing.driver_number;