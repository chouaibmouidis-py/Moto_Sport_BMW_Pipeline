"""Build enriched stops and participant summaries, preserving existing SQL and blocking checks."""

import logging

from .quality import build_source_pairs, validate_entry_links, validate_race_car_summary
from .queries import build_view
from .quality import validate_gold_participant_keys
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


def build_pit_stop_counts(connection, project_directory, stops):
    """Apply the shared count query to the supplied Silver stop relation."""
    stops.create_view("pit_stop_count_input")
    return build_view(
        connection, project_directory, "28_pit_stop_counts_by_car.sql",
        "pit_stop_counts_by_car",
    )

def build_pit_stop_summary(connection, project_directory, stops):
    """Apply shared duration statistics to the supplied Silver stop relation."""
    stops.create_view("pit_stop_summary_input")

    return build_view(
        connection,
        project_directory,
        "06_pit_stop_summary.sql",
        "pit_stop_summary",
    )


def build_classification_marts(connection, project_directory):
    build_pit_stop_counts(
        connection, project_directory, connection.table("silver_pit_stops"),
    )
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
    build_pit_stop_summary(
        connection,
        project_directory,
        connection.table("silver_pit_stops"),
    )
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


def build_csv_pdf_race_summary(connection, project_directory):
    """Pair loaded Silver reports and preserve classification participants.

    A source must have exactly one loaded version; callers select the intended
    files before building this mart. Catalog metadata declares the session pair.
    """
    build_source_pairs(connection, project_directory)
    for view_name, version_fields in (
        ("silver_classification_csv", "source_id, bronze_sha256"),
        ("silver_pdf_pit_stops", "source_id, bronze_sha256, pdf_sha256"),
    ):
        ambiguous = connection.sql(f"""
            SELECT source_id
            FROM (SELECT DISTINCT {version_fields} FROM {view_name})
            GROUP BY source_id
            HAVING COUNT(*) > 1
        """).fetchall()
        if ambiguous:
            raise ValueError(f"CSV/PDF summary rejected: multiple source versions: {ambiguous}")

    build_pit_stop_counts(
        connection, project_directory, connection.table("silver_pdf_pit_stops"),
    )

    build_pit_stop_summary(
        connection,
        project_directory,
        connection.table("silver_pdf_pit_stops"),
    )


    orphan_stops = connection.sql("""
        SELECT DISTINCT counts.source_id, counts.car_number
        FROM pit_stop_counts_by_car AS counts
        LEFT JOIN classification_pit_stop_sources AS pairs
            ON counts.source_id = pairs.pit_stop_source_id
        LEFT JOIN silver_classification_csv AS classification
            ON classification.source_id = pairs.classification_source_id
            AND classification.car_number = counts.car_number
        WHERE classification.source_id IS NULL
    """).fetchall()
    if orphan_stops:
        raise ValueError(f"CSV/PDF summary rejected: stops without classification: {orphan_stops}")

    summary = build_view(
        connection, project_directory, "35_csv_pdf_race_summary.sql",
        "csv_pdf_race_summary",
    )
    expected = connection.table("silver_classification_csv").count("*").fetchone()[0]
    if summary.count("*").fetchone()[0] != expected:
        raise ValueError("CSV/PDF summary rejected: participant count changed")
    unmatched = summary.filter(
        "pit_stop_source_id IS NULL OR session_id IS NULL"
    ).count("*").fetchone()[0]
    if unmatched:
        raise ValueError("CSV/PDF summary rejected: missing source pairing or context")
    return summary

def build_manufacturer_reference(connection, project_directory):
    """Resolve manufacturer names from explicit, versioned Bronze evidence."""
    build_view(
        connection,
        project_directory,
        "37_manufacturer_reference_input.sql",
        "manufacturer_reference_input",
    )

    return build_view(
        connection,
        project_directory,
        "36_manufacturer_reference.sql",
        "manufacturer_reference",
    )

def enrich_2023_manufacturers(connection, project_directory):
    """Enrich participants without changing their number of rows."""
    expected_count = connection.table(
        "csv_pdf_race_summary"
    ).count("*").fetchone()[0]

    participants = build_view(
        connection,
        project_directory,
        "38_enrich_2023_manufacturers.sql",
        "enriched_2023_participants",
    )

    actual_count = participants.count("*").fetchone()[0]

    if actual_count != expected_count:
        raise ValueError(
            "Manufacturer enrichment rejected: participant count changed"
        )

    return participants

def build_gold_race_car_summary(connection, project_directory):
    """Stack aligned season participants without dropping or adding rows."""
    expected_count = sum(
        connection.table(view_name).count("*").fetchone()[0]
        for view_name in (
            "enriched_2023_participants",
            "json_race_car_summary",
        )
    )

    participants = build_view(
        connection,
        project_directory,
        "39_gold_race_car_summary.sql",
        "gold_race_car_summary",
    )

    actual_count = participants.count("*").fetchone()[0]

    if actual_count != expected_count:
        raise ValueError(
            "Gold rejected: participant count changed"
        )

    validate_gold_participant_keys(connection)

    return participants