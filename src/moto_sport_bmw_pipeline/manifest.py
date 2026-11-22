"""Select source documents and pair reports independently of storage format."""

from pathlib import Path


SUPPORTED_REPORTS = {
    ("classification", "json"), ("classification", "csv"),
    ("pit_stops", "json"), ("pit_stops", "pdf"),
}


def select_documents(manifest, *, season=None, event_id=None):
    validate_unique_source_ids(manifest["documents"])
    selected = []
    for source in manifest["documents"]:
        if not source.get("enabled", False):
            continue
        if season is not None and source["season"] != season:
            continue
        if event_id is not None and source["event_id"] != event_id:
            continue
        report_format = source.get("format", "json")
        if not isinstance(report_format, str):
            raise ValueError(f"Invalid format for source {source['source_id']}")
        report_format = report_format.lower()
        if (source["document_type"], report_format) not in SUPPORTED_REPORTS:
            raise ValueError(f"Unsupported report: {source['document_type']}/{report_format}")
        for field in ("source_id", "filename"):
            value = source[field]
            if value in (".", "..") or Path(value).name != value or "\\" in value:
                raise ValueError(f"Unsafe {field}: {value}")
        selected.append({**source, "format": report_format})
    if not selected:
        raise ValueError("Manifest rejected: no selected sources")
    pair_reports(selected)
    return selected


def pair_reports(documents):
    pairs = {}
    for source in documents:
        key = tuple(source[field] for field in ("championship", "season", "event_id", "session_id"))
        reports = pairs.setdefault(key, {})
        role = source["document_type"]
        if role in reports:
            raise ValueError(f"Ambiguous {role} report for session {key}")
        reports[role] = source
    for key, reports in pairs.items():
        if set(reports) != {"classification", "pit_stops"}:
            raise ValueError(f"Missing paired report for session {key}")
        formats = tuple(reports[role].get("format", "json") for role in ("classification", "pit_stops"))
        if formats not in (("json", "json"), ("csv", "pdf")):
            raise ValueError(f"Unsupported report pairing for session {key}: {formats}")
    return list(pairs.values())
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
