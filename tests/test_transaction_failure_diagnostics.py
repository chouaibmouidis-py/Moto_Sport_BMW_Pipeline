"""Preserve the primary failure when transaction rollback also fails."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import archive_sources
from migrate_motherduck_schema import migrate_schema
from publish_motherduck import publish_gold


class TransactionFailureDiagnosticsTests(unittest.TestCase):
    def test_publication_preserves_original_exception_when_rollback_fails(self):
        connection = MagicMock()
        connection.sql.return_value.columns = ['car_number', 'publication_run_id']
        original = ConnectionError('Connection lost during publication')

        def execute(sql, *args):
            if sql.strip() == 'ROLLBACK':
                raise RuntimeError('Connection unavailable for rollback')
            if 'DELETE FROM' in sql:
                raise original
            return MagicMock()

        connection.execute.side_effect = execute
        with self.assertLogs('moto_sport_bmw_pipeline.publish_motherduck', level='ERROR') as captured:
            with self.assertRaises(ConnectionError) as raised:
                publish_gold(connection, Path('unused.parquet'), 'candidate')
        self.assertIs(raised.exception, original)
        self.assertIn('Rollback failed', '\n'.join(captured.output))
        self.assertIn('Connection unavailable for rollback', '\n'.join(captured.output))
        self.assertFalse(any(call.args[0].strip() == 'COMMIT' for call in connection.execute.call_args_list))

    def test_migration_preserves_original_exception_when_rollback_fails(self):
        connection = MagicMock()
        connection.read_parquet.return_value.columns = ['car_number', 'team_name']
        connection.read_parquet.return_value.types = ['VARCHAR', 'VARCHAR']
        original = ConnectionError('Connection lost during migration')

        def execute(sql, *args):
            if sql.strip() == 'ROLLBACK':
                raise RuntimeError('Connection unavailable for rollback')
            if sql.startswith('DESCRIBE'):
                result = MagicMock()
                result.fetchall.return_value = [('car_number', 'VARCHAR'), ('publication_run_id', 'VARCHAR')]
                return result
            if sql.startswith('SELECT * FROM bmw_analytics.main.gold_history'):
                raise original
            return MagicMock()

        connection.execute.side_effect = execute
        with self.assertLogs('moto_sport_bmw_pipeline.migrate_motherduck_schema', level='ERROR') as captured:
            with self.assertRaises(ConnectionError) as raised:
                migrate_schema(connection, Path('unused.parquet'), apply=True)
        self.assertIs(raised.exception, original)
        self.assertIn('Rollback failed', '\n'.join(captured.output))
        self.assertFalse(any(call.args[0].strip() == 'COMMIT' for call in connection.execute.call_args_list))

    def test_archive_keeps_pin_and_original_exception_when_rollback_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'config').mkdir()
            raw = root / 'data/raw/example/report.json'
            raw.parent.mkdir(parents=True)
            raw.write_bytes(b'{}')
            (root / 'config/sources.json').write_text(json.dumps({'documents': [{
                'source_id': 'example', 'enabled': True, 'filename': 'report.json',
                'expected_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
            }]}))
            pin = root / 'config/source_archive.json'
            pin.write_text('{"archive_id": "previous", "file_count": 1}')
            before = pin.read_bytes()
            connection = MagicMock()
            connection.__enter__.return_value = connection
            original = ConnectionError('Connection lost during archival')

            def execute(sql, *args):
                if sql.strip() == 'ROLLBACK':
                    raise RuntimeError('Connection unavailable for rollback')
                if 'INSERT INTO' in sql:
                    raise original
                return MagicMock()

            connection.execute.side_effect = execute
            with patch.object(archive_sources, 'PROJECT_DIR', root), patch.object(
                archive_sources.duckdb, 'connect', return_value=connection
            ), patch.dict('os.environ', {'motherduck_token': 'local-test-only'}), patch(
                'sys.argv', ['archive_sources.py', '--pin']
            ):
                with self.assertLogs('moto_sport_bmw_pipeline.archive_sources', level='ERROR') as captured:
                    with self.assertRaises(ConnectionError) as raised:
                        archive_sources.main()
                self.assertIs(raised.exception, original)
                self.assertEqual(pin.read_bytes(), before)
                self.assertIn('Rollback failed', '\n'.join(captured.output))
