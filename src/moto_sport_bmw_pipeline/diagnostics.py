"""Display bounded exploration tables only when verbose mode is explicitly requested."""

import logging

logger = logging.getLogger(__name__)


def show_pipeline_tables(connection):
    """Keep interactive table output separate from operational log messages."""
    for view in (
        "classification_pit_stop_sources",
        "silver_sessions", "silver_car_entries", "silver_driver_entries",
        "silver_pit_stops", "session_quality_summary",
        "total_pit_duration_quality", "total_pit_duration_comparison",
        "enriched_pit_stops", "classification_pit_stop_comparison",
        "race_car_summary", "classification_count_quality",
    ):
        logger.debug("Diagnostic table: %s", view)
        connection.table(view).show(max_rows=20)
