"""Read version-controlled SQL and register the resulting view in the active connection."""

import logging

logger = logging.getLogger(__name__)

def build_view(connection, project_directory, filename, view_name):
    query = (project_directory / "sql" / filename).read_text(encoding="utf-8")
    try:
        result = connection.sql(query)
        result.create_view(view_name)
    except Exception:
        logger.exception("SQL view failed: file=%s view=%s", filename, view_name)
        raise
    return result
