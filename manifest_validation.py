def validate_unique_source_ids(documents):
    seen_source_ids = []

    for index, document in enumerate(documents):
        source_id = document.get("source_id")

        if source_id is None:
            raise ValueError(
                f"Document at index {index}: missing source_id"
            )

        if not isinstance(source_id, str):
            raise ValueError(
                f"Document at index {index}: source_id must be a string"
            )

        if not source_id.strip():
            raise ValueError(
                f"Document at index {index}: source_id must not be blank"
            )

        if source_id in seen_source_ids:
            raise ValueError(
                f"Duplicate source_id: {source_id}"
            )

        seen_source_ids.append(source_id)