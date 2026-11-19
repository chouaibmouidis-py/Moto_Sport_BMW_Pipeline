"""Publish the active local Gold run to MotherDuck."""

from moto_sport_bmw_pipeline.paths import PROJECT_DIR
from moto_sport_bmw_pipeline.run_reference import get_current_run
import getpass
import os
import duckdb

def main():

    gold_directory = PROJECT_DIR / "data" / "gold"
    run_directory = get_current_run(gold_directory)
    mart_path = run_directory / "race_car_summary.parquet"

    if not mart_path.is_file():
        raise FileNotFoundError(f"Gold mart not found: {mart_path}")

    if not os.environ.get("motherduck_token"):
        os.environ["motherduck_token"] = getpass.getpass(
            "Token MotherDuck : "
        ).strip()

    with duckdb.connect("md:bmw_analytics") as connection:
        local_gold = connection.read_parquet(str(mart_path))
        publication_run_id = run_directory.name

        publication = connection.sql(
            "SELECT *, ? AS publication_run_id FROM local_gold",
            params=[publication_run_id],
        )

        connection.execute("""
            CREATE TABLE IF NOT EXISTS bmw_analytics.main.gold_history AS
            SELECT *
            FROM publication
            WHERE FALSE
        """)

        connection.execute("BEGIN TRANSACTION")

        try:
            connection.execute(
                """
                DELETE FROM bmw_analytics.main.gold_history
                WHERE publication_run_id = ?
                """,
                [publication_run_id],
            )

            connection.execute("""
                INSERT INTO bmw_analytics.main.gold_history BY NAME
                SELECT * FROM publication
            """)

            expected_count = publication.count("*").fetchone()[0]

            saved_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM bmw_analytics.main.gold_history
                WHERE publication_run_id = ?
                """,
                [publication_run_id],
            ).fetchone()[0]

            if saved_count != expected_count:
                raise ValueError(
                    f"Gold publication rejected: expected {expected_count} "
                    f"rows, saved {saved_count}"
                )

            different_row_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT * FROM publication
                    EXCEPT ALL
                    SELECT *
                    FROM bmw_analytics.main.gold_history
                    WHERE publication_run_id = ?
                ) AS differences
                """,
                [publication_run_id],
            ).fetchone()[0]

            if different_row_count > 0:
                raise ValueError(
                    "Gold publication rejected: saved content differs"
                )

            connection.execute("""
                CREATE TABLE IF NOT EXISTS
                    bmw_analytics.main.current_gold_run (
                        publication_run_id VARCHAR NOT NULL
                    )
            """)

            connection.execute(
                "DELETE FROM bmw_analytics.main.current_gold_run"
            )

            connection.execute(
                """
                INSERT INTO bmw_analytics.main.current_gold_run
                VALUES (?)
                """,
                [publication_run_id],
            )

            connection.execute("""
                CREATE OR REPLACE VIEW
                    bmw_analytics.main.race_car_summary AS
                SELECT history.*
                FROM bmw_analytics.main.gold_history AS history
                JOIN bmw_analytics.main.current_gold_run AS current_run
                    ON history.publication_run_id
                       = current_run.publication_run_id
            """)

            connection.execute("COMMIT")

        except Exception:
            connection.execute("ROLLBACK")
            raise

        connection.execute("""
            CREATE SHARE IF NOT EXISTS bmw_gold
            FROM bmw_analytics (
                ACCESS RESTRICTED,
                VISIBILITY DISCOVERABLE,
                UPDATE AUTOMATIC
            )
        """)

        connection.execute("""
            GRANT READ ON SHARE bmw_gold TO ROLE explorer
        """)

        connection.sql("""
            SELECT publication_run_id, COUNT(*) AS participant_count
            FROM bmw_analytics.main.race_car_summary
            GROUP BY publication_run_id
        """).show()

if __name__ == "__main__":
    main()