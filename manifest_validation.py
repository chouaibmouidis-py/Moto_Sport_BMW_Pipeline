def validate_unique_source_ids(documents):
    seen_source_ids = []

    for document in documents:
        source_id = document["source_id"]

        if source_id in seen_source_ids:
            raise ValueError(
                f"Duplicate source_id: {source_id}"
            )

        seen_source_ids.append(source_id)