"""Read version-controlled SQL and register the resulting view in the active connection."""

def build_view(connection, project_directory, filename, view_name):
    query = (project_directory / "sql" / filename).read_text(encoding="utf-8")
    result = connection.sql(query)
    result.create_view(view_name)
    return result
