"""Test the additive migration with local DuckDB, never remote credentials."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import duckdb
from migrate_motherduck_schema import SPORTING_COLUMNS, migrate_schema
from publish_motherduck import publish_gold


class MotherDuckMigrationTests(unittest.TestCase):
    def prepare(self, connection, directory):
        connection.execute("ATTACH ':memory:' AS bmw_analytics")
        old = Path(directory) / 'old.parquet'
        new = Path(directory) / 'new.parquet'
        connection.sql("SELECT '04' AS car_number").write_parquet(str(old))
        publish_gold(connection, old, 'old-run')
        fields = ', '.join(f'NULL::{kind} AS {name}' for name, kind in SPORTING_COLUMNS.items())
        connection.sql("SELECT '04' AS car_number, " + fields).write_parquet(str(new))
        return new

    def test_inspection_does_not_change_schema(self):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as connection:
            new = self.prepare(connection, directory)
            self.assertEqual(migrate_schema(connection, new), SPORTING_COLUMNS)
            self.assertEqual(len(connection.sql('SELECT * FROM bmw_analytics.main.gold_history').columns), 2)

    def test_adds_columns_preserves_old_publication_then_accepts_new_run(self):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as connection:
            new = self.prepare(connection, directory)
            self.assertEqual(migrate_schema(connection, new, apply=True), SPORTING_COLUMNS)
            self.assertEqual(connection.sql('SELECT * FROM bmw_analytics.main.race_car_summary').fetchall(), [('04', 'old-run')])
            self.assertEqual(connection.sql('SELECT * FROM bmw_analytics.main.current_gold_run').fetchall(), [('old-run',)])
            self.assertEqual(migrate_schema(connection, new, apply=True), {})
            publish_gold(connection, new, 'new-run')
            self.assertEqual(connection.sql('SELECT publication_run_id FROM bmw_analytics.main.race_car_summary').fetchall(), [('new-run',)])
            self.assertEqual(connection.sql('SELECT COUNT(*) FROM bmw_analytics.main.gold_history').fetchone()[0], 2)

    def test_rejects_type_change_before_writing(self):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as connection:
            new = self.prepare(connection, directory)
            connection.execute('ALTER TABLE bmw_analytics.main.gold_history ALTER car_number TYPE INTEGER')
            with self.assertRaisesRegex(ValueError, 'incompatible column car_number'):
                migrate_schema(connection, new, apply=True)
            self.assertEqual(len(connection.sql('SELECT * FROM bmw_analytics.main.gold_history').columns), 2)

    def test_failure_during_addition_rolls_back_schema_and_view(self):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as connection:
            new = self.prepare(connection, directory)
            # First ADD succeeds, the second is made invalid to check transactional rollback.
            with patch('migrate_motherduck_schema.quote_identifier', side_effect=lambda name: 'INVALID SQL !' if name == 'completed_laps' else '"' + name + '"'):
                with self.assertRaises(duckdb.Error):
                    migrate_schema(connection, new, apply=True)
            self.assertEqual(len(connection.sql('SELECT * FROM bmw_analytics.main.gold_history').columns), 2)
            self.assertEqual(connection.sql('SELECT * FROM bmw_analytics.main.race_car_summary').fetchall(), [('04', 'old-run')])
