"""Pin the local archive reference only after verified archival succeeds."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import duckdb
import archive_sources


class SourceArchivePinTests(unittest.TestCase):
    def test_success_pins_inventory_and_failure_keeps_previous_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'config').mkdir()
            raw = root / 'data/raw/example/report.json'
            raw.parent.mkdir(parents=True)
            raw.write_bytes(b'{"classification": []}')
            (root / 'config/sources.json').write_text(json.dumps({'documents': [{
                'source_id': 'example', 'enabled': True, 'filename': 'report.json',
                'expected_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
            }]}))
            reference = root / 'config/source_archive.json'
            reference.write_text('{"archive_id": "previous", "file_count": 1}')
            database = root / 'archive.duckdb'
            connect = duckdb.connect

            def local_connection(_):
                connection = connect()
                connection.execute("ATTACH '" + str(database).replace("'", "''") + "' AS bmw_analytics")
                return connection

            with patch.object(archive_sources, 'PROJECT_DIR', root), patch.object(
                archive_sources.duckdb, 'connect', side_effect=local_connection
            ), patch.dict('os.environ', {'motherduck_token': 'local-test-only'}), patch(
                'sys.argv', ['archive_sources.py', '--pin']
            ):
                archive_sources.main()
                verified = json.loads(reference.read_text())
                self.assertNotEqual(verified['archive_id'], 'previous')
                self.assertEqual(verified['file_count'], 1)
                with local_connection(None) as connection:
                    connection.execute("UPDATE bmw_analytics.main.source_archive SET content = 'corrupted'::BLOB")
                reference.write_text('{"archive_id": "previous", "file_count": 1}')
                with self.assertRaisesRegex(ValueError, 'saved content differs'):
                    archive_sources.main()
                self.assertEqual(json.loads(reference.read_text())['archive_id'], 'previous')
