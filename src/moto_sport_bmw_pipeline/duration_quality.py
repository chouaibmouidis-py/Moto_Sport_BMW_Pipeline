"""Build duration diagnostics without turning reportable source anomalies into blocking errors."""

import logging

from .quality import build_total_duration_quality
from .queries import build_view

logger = logging.getLogger(__name__)


def report_issues(label, relation, *, verbose=False):
    count = relation.count("*").fetchone()[0]
    if count:
        logger.warning("%s: %s", label, count)
        if verbose:
            relation.limit(20).show()
    else:
        logger.info("%s: 0", label)
    return count


def build_duration_reports(connection, project_directory, *, verbose=False):
    build_total_duration_quality(connection, project_directory)
    totals = build_view(
        connection, project_directory, "24_compare_total_pit_durations.sql",
        "total_pit_duration_comparison",
    )
    logger.info("Cars with pit stops: %s", totals.count("*").fetchone()[0])
    report_issues(
        "Total duration comparison issues",
        totals.filter("comparison_status != 'matched'"), verbose=verbose,
    )
    missing = connection.sql(
        (project_directory / "sql" / "22_check_missing_total_pit_durations.sql")
        .read_text(encoding="utf-8")
    )
    report_issues("Unconverted total pit durations", missing, verbose=verbose)
    durations = connection.table("silver_pit_stops").filter("""
        clock_duration_seconds IS NULL OR pit_time_in_seconds IS NULL
        OR ABS(clock_duration_seconds - pit_time_in_seconds) > 0.001
    """)
    report_issues("Duration comparison issues", durations, verbose=verbose)
