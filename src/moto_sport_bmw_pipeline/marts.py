"""Build enriched stops and participant summaries, preserving existing SQL and blocking checks."""

import logging

from .quality import validate_entry_links, validate_race_car_summary
from .queries import build_view

logger = logging.getLogger(__name__)


def build_enriched_stops(connection, project_directory):
    links = connection.sql(
        (project_directory / "sql" / "19_check_pit_stop_driver_links.sql")
        .read_text(encoding="utf-8")
    )
    invalid = links.filter("link_status IN ('unmatched', 'ambiguous')").count("*").fetchone()[0]
    if invalid:
        raise ValueError("Silver rejected: unmatched or ambiguous driver links")
    missing = links.filter("link_status = 'missing'").count("*").fetchone()[0]
    if missing:
        logger.warning("Missing driver references: %s", missing)
    else:
        logger.info("Missing driver references: 0")
    enriched = build_view(
        connection, project_directory, "20_enriched_pit_stops.sql", "enriched_pit_stops",
    )
    matched_drivers, matched_stops = validate_entry_links(connection, project_directory)
    logger.info("Matched driver entries: %s", matched_drivers)
    logger.info("Matched pit stops: %s", matched_stops)
    if enriched.count("*").fetchone()[0] != connection.table("silver_pit_stops").count("*").fetchone()[0]:
        raise ValueError("Enriched stops rejected: row count mismatch")
    logger.info("Enriched pit stops: %s", matched_stops)
    return enriched


def build_classification_marts(connection, project_directory):
    build_view(connection, project_directory, "28_pit_stop_counts_by_car.sql", "pit_stop_counts_by_car")
    comparison = build_view(
        connection, project_directory, "30_classification_pit_stop_comparison.sql",
        "classification_pit_stop_comparison",
    )
    expected = connection.table("silver_classification").count("*").fetchone()[0]
    actual = comparison.count("*").fetchone()[0]
    if actual != expected:
        raise ValueError(
            "Classification comparison rejected: participant count "
            f"changed from {expected} to {actual}"
        )
    logger.info("Classification comparison rows: %s", actual)
    build_view(connection, project_directory, "06_pit_stop_summary.sql", "pit_stop_summary")
    summary = build_view(connection, project_directory, "31_race_car_summary.sql", "race_car_summary")
    validate_race_car_summary(connection)
    quality = build_view(
        connection, project_directory, "32_classification_count_quality.sql",
        "classification_count_quality",
    )
    mismatches = quality.aggregate("SUM(count_mismatch_count)").fetchone()[0] or 0
    if mismatches:
        logger.warning("Classification count mismatches reported: %s (non-blocking)", mismatches)
    return summary
