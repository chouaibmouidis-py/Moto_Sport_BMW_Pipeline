"""Configure dashboard sharing separately from Gold data publication."""

import getpass
import logging
import os

import duckdb

from moto_sport_bmw_pipeline.logging_config import configure_logging, log_operation

logger = logging.getLogger("moto_sport_bmw_pipeline.configure_motherduck_share")


def configure_share(connection):
    """Create the share if absent and grant the dashboard role read access."""
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


def main():
    configure_logging()
    if not os.environ.get("motherduck_token"):
        os.environ["motherduck_token"] = getpass.getpass("Token MotherDuck : ").strip()
    with log_operation(logger, "Configure MotherDuck dashboard share",
                       stage="motherduck_sharing", source_id="-"):
        with duckdb.connect("md:bmw_analytics") as connection:
            configure_share(connection)


if __name__ == "__main__":
    main()
