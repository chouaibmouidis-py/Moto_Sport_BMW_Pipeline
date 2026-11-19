"""Display published IMSA Gold data from MotherDuck in an interactive dashboard."""

import os

import duckdb
import streamlit as st


def event_label(event_id):
    """Format an event identifier for display."""
    if event_id == "vir":
        return "VIR"
    return event_id.replace("-", " ").title()


@st.cache_data(ttl=300, show_spinner=False)
def load_gold_snapshot():
    """Read one published snapshot; limit remote reads to once per five minutes."""
    os.environ["motherduck_token"] = st.secrets["motherduck_token"]

    with duckdb.connect("md:bmw_analytics") as remote_connection:
        remote_connection.execute("REFRESH DATABASE bmw_analytics")

        return remote_connection.sql("""
            SELECT *
            FROM bmw_analytics.main.race_car_summary
        """).df()


@st.fragment(run_every="5min")
def render_dashboard():
    """Refresh the displayed snapshot while the browser session remains active."""
    st.title("BMW Motorsport — IMSA")

    if st.button("Refresh data"):
        load_gold_snapshot.clear()

    try:
        gold_snapshot = load_gold_snapshot()
    except (duckdb.Error, FileNotFoundError, KeyError):
        st.error("Published data is temporarily unavailable. Please try refreshing shortly.")
        return

    if gold_snapshot.empty:
        st.warning("Published Gold data is unavailable.")
        return

    publication_run_id = gold_snapshot["publication_run_id"].iloc[0]
    st.caption(f"Published Gold run · {publication_run_id}")
    st.caption("Checks for updates every five minutes while this page is open.")

    with duckdb.connect() as connection:
        participants = connection.from_df(gold_snapshot)
        participants.create_view("gold_participants")

        season_filter, event_filter, class_filter = st.columns(3)

        season_rows = (
            participants.project("season")
            .distinct()
            .order("season")
            .fetchall()
        )

        seasons = [row[0] for row in season_rows]

        selected_season = season_filter.selectbox("Season", seasons)

        event_rows = connection.sql(
            """
            SELECT DISTINCT event_id
            FROM gold_participants
            WHERE season = ?
            ORDER BY event_id
            """,
            params=[selected_season],
        ).fetchall()

        events = [row[0] for row in event_rows]

        selected_event = event_filter.selectbox(
            "Event",
            events,
            format_func=event_label,
        )

        class_rows = connection.sql(
            """
            SELECT DISTINCT car_class
            FROM gold_participants
            WHERE manufacturer = 'BMW'
            AND season = ?
            AND event_id = ?
            AND car_class IS NOT NULL
            ORDER BY car_class
            """,
            params=[selected_season, selected_event],
        ).fetchall()

        classes = [row[0] for row in class_rows]

        selected_class = class_filter.selectbox(
            "Class",
            ["All classes"] + classes,
        )

        bmw_participants = connection.sql(
            """
            SELECT *
            FROM gold_participants
            WHERE manufacturer = 'BMW'
            AND season = ?
            AND event_id = ?
            AND (? = 'All classes' OR car_class = ?)
            """,
            params=[
                selected_season,
                selected_event,
                selected_class,
                selected_class,
            ],
        )

        table = bmw_participants.project("""
            season,
            event_id,
            car_number,
            car_model,
            car_class,
            overall_position,
            classification_status,
            not_finished,
            reported_pit_stop_count,
            observed_pit_stop_count,
            average_pit_time_seconds,
            valid_duration_count,
            invalid_duration_count,
            duration_coverage_percent,
            comparison_status,
            stop_detail_status
        """).order("season, event_id, overall_position").df()

        if table.empty:
            st.caption("0 BMW participants for the current selection.")
            return

        provenance = bmw_participants.project("""
            session_id,
            source_id,
            bronze_sha256,
            pit_stop_source_id,
            pit_stop_bronze_sha256,
            pdf_sha256
        """).distinct().df()

        quality = bmw_participants.filter("""
            comparison_status = 'count_mismatch'
            OR stop_detail_status IN (
                'no_stop_details',
                'missing_pit_stop_report'
            )
            OR invalid_duration_count > 0
        """).project("""
            car_number,
            car_class,
            reported_pit_stop_count,
            observed_pit_stop_count,
            invalid_duration_count,
            comparison_status,
            stop_detail_status
        """).order("car_number").df()

        participant_column, missing_column = st.columns(2)

        participant_column.metric(
            "BMW participants",
            len(table),
        )

        missing_column.metric(
            "Participants without stop details",
            int(table["observed_pit_stop_count"].isna().sum()),
        )

    st.dataframe(
        table,
        hide_index=True,
        column_config={
            "season": "Season",
            "event_id": "Event",
            "car_number": "Car",
            "car_model": "Model",
            "car_class": "Class",
            "overall_position": "Overall position",
            "classification_status": "Classification status",
            "not_finished": "Did not finish",
            "reported_pit_stop_count": st.column_config.NumberColumn(
                "Reported stops",
                format="%d",
                help=(
                    "Stop count declared in the classification report. "
                    "Unavailable in the 2023 CSV reports."
                ),
            ),
            "observed_pit_stop_count": "Observed stops",
            "average_pit_time_seconds": st.column_config.NumberColumn(
                "Average duration (s)",
                format="%.3f",
                help=(
                    "Mean recorded duration across stops with a converted duration, "
                    "expressed in seconds."
                ),
            ),
            "valid_duration_count": "Converted durations",
            "invalid_duration_count": "Unconverted durations",
            "duration_coverage_percent": st.column_config.NumberColumn(
                "Duration coverage",
                format="%.2f%%",
                help=(
                    "Converted stop durations divided by observed stop records, "
                    "multiplied by 100."
                ),
            ),
            "comparison_status": "Count comparison",
            "stop_detail_status": "Stop details",
        },
    )

    with st.expander("Quality signals", expanded=True):
        if quality.empty:
            st.caption("0 participants flagged by these three checks.")
        else:
            st.dataframe(
                quality,
                hide_index=True,
                column_config={
                    "car_number": "Car",
                    "car_class": "Class",
                    "reported_pit_stop_count": "Reported stops",
                    "observed_pit_stop_count": "Observed stops",
                    "invalid_duration_count": "Unconverted durations",
                    "comparison_status": "Count comparison",
                    "stop_detail_status": "Stop details",
                },
            )

    st.subheader("Average recorded pit duration by car")

    chart_data = table.dropna(
        subset=["average_pit_time_seconds"]
    )

    if chart_data.empty:
        st.caption("0 recorded average durations available for this selection.")
    else:
        st.bar_chart(
            chart_data,
            x="car_number",
            y="average_pit_time_seconds",
            color="car_class",
            x_label="Car number",
            y_label="Average duration (seconds)",
        )

    with st.expander("Source reports"):
        st.dataframe(
            provenance,
            hide_index=True,
            column_config={
                "session_id": "Session",
                "source_id": "Classification source",
                "bronze_sha256": "Classification Bronze SHA-256",
                "pit_stop_source_id": "Pit-stop source",
                "pit_stop_bronze_sha256": "Pit-stop Bronze SHA-256",
                "pdf_sha256": "PDF SHA-256",
            },
        )


def main():
    st.set_page_config(
        page_title="BMW Motorsport — IMSA",
        layout="wide",
    )
    render_dashboard()


if __name__ == "__main__":
    main()
