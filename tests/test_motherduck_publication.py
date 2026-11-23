"""Exercise data transactions locally, independently of share provisioning."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import duckdb

from configure_motherduck_share import configure_share
from publish_motherduck import publish_gold


class MotherDuckPublicationTests(unittest.TestCase):
    def test_publishes_data_without_share_commands(self):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as connection:
            connection.execute("ATTACH ':memory:' AS bmw_analytics")
            path = Path(directory) / "summary.parquet"
            connection.sql("SELECT '04' AS car_number").write_parquet(str(path))
            publish_gold(connection, path, "run-a")
            publish_gold(connection, path, "run-a")
            self.assertEqual(connection.sql(
                "SELECT car_number, publication_run_id "
                "FROM bmw_analytics.main.race_car_summary"
            ).fetchall(), [("04", "run-a")])

    def test_publication_failure_rolls_back_data_and_reference(self):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as connection:
            connection.execute("ATTACH ':memory:' AS bmw_analytics")
            path = Path(directory) / "summary.parquet"
            connection.sql("SELECT '04' AS car_number").write_parquet(str(path))
            publish_gold(connection, path, "run-a")
            # A table blocks replacement by a view, after the candidate was inserted.
            connection.execute("DROP VIEW bmw_analytics.main.race_car_summary")
            connection.execute("CREATE TABLE bmw_analytics.main.race_car_summary (blocked INTEGER)")
            with self.assertRaises(duckdb.Error):
                publish_gold(connection, path, "run-b")
            self.assertEqual(connection.sql(
                "SELECT * FROM bmw_analytics.main.current_gold_run"
            ).fetchall(), [("run-a",)])
            self.assertEqual(connection.sql(
                "SELECT DISTINCT publication_run_id FROM bmw_analytics.main.gold_history"
            ).fetchall(), [("run-a",)])

    def test_share_configuration_has_no_data_publication_commands(self):
        connection = Mock()
        configure_share(connection)
        commands = [call.args[0].strip() for call in connection.execute.call_args_list]
        self.assertEqual(len(commands), 2)
        self.assertTrue(commands[0].startswith("CREATE SHARE IF NOT EXISTS bmw_gold"))
        self.assertEqual(commands[1], "GRANT READ ON SHARE bmw_gold TO ROLE explorer")

    def test_share_failure_is_propagated(self):
        connection = Mock()
        connection.execute.side_effect = RuntimeError("Share access denied")
        with self.assertRaisesRegex(RuntimeError, "Share access denied"):
            configure_share(connection)