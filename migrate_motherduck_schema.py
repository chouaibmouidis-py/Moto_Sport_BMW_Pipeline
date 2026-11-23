"""Add sporting Gold columns without publishing a run or changing its active pointer."""

import argparse
from collections import Counter
import getpass
import logging
import os
from pathlib import Path

import duckdb

from moto_sport_bmw_pipeline.logging_config import configure_logging, log_operation
from moto_sport_bmw_pipeline.paths import PROJECT_DIR
from moto_sport_bmw_pipeline.run_reference import get_current_run

logger = logging.getLogger('moto_sport_bmw_pipeline.migrate_motherduck_schema')

SPORTING_COLUMNS = {
    'team_name': 'VARCHAR', 'completed_laps': 'INTEGER',
    'fastest_lap_number': 'INTEGER', 'fastest_lap_speed_kph': 'DOUBLE',
    'total_time_raw': 'VARCHAR', 'total_time_seconds': 'DOUBLE',
    'fastest_lap_time_raw': 'VARCHAR', 'fastest_lap_time_seconds': 'DOUBLE',
    'gap_first_raw': 'VARCHAR', 'gap_previous_raw': 'VARCHAR',
    'gap_first_kind': 'VARCHAR', 'gap_first_seconds': 'DOUBLE',
    'gap_first_laps': 'INTEGER', 'gap_previous_kind': 'VARCHAR',
    'gap_previous_seconds': 'DOUBLE', 'gap_previous_laps': 'INTEGER',
}


def quote_identifier(value):
    return '"' + value.replace('"', '""') + '"'


def migrate_schema(connection, mart_path: Path, *, apply=False):
    """Reject schema drift; only add the known sporting columns, transactionally."""
    candidate = connection.read_parquet(str(mart_path))
    expected = dict(zip(candidate.columns, map(str, candidate.types)))
    expected['publication_run_id'] = 'VARCHAR'
    history = 'bmw_analytics.main.gold_history'
    actual = dict((row[0], row[1]) for row in connection.execute(
        f'DESCRIBE SELECT * FROM {history}'
    ).fetchall())
    for name, kind in actual.items():
        if expected.get(name) != kind:
            raise ValueError(f'Gold schema migration rejected: incompatible column {name}: {kind}')
    missing = {name: kind for name, kind in expected.items() if name not in actual}
    if any(SPORTING_COLUMNS.get(name) != kind for name, kind in missing.items()):
        raise ValueError(f'Gold schema migration rejected: unexpected missing columns: {list(missing)}')
    logger.info('Missing Gold columns: %s', list(missing))
    if not apply or not missing:
        return missing

    connection.execute('BEGIN TRANSACTION')
    try:
        before = connection.execute(f'SELECT * FROM {history}').fetchall()
        active_before = connection.execute('SELECT * FROM bmw_analytics.main.current_gold_run').fetchall()
        visible = 'bmw_analytics.main.race_car_summary'
        visible_columns = [row[0] for row in connection.execute(f'DESCRIBE SELECT * FROM {visible}').fetchall()]
        visible_before = connection.execute(f'SELECT * FROM {visible}').fetchall()
        # Freeze the existing public projection before adding columns to its source.
        projection = ', '.join('history.' + quote_identifier(name) for name in visible_columns)
        connection.execute(f'''
            CREATE OR REPLACE VIEW {visible} AS
            SELECT {projection} FROM {history} AS history
            JOIN bmw_analytics.main.current_gold_run AS current_run
            ON history.publication_run_id = current_run.publication_run_id
        ''')
        for name, kind in missing.items():
            connection.execute(f'ALTER TABLE {history} ADD COLUMN {quote_identifier(name)} {kind}')
        projection = ', '.join(quote_identifier(name) for name in actual)
        # Compare multiplicities without depending on row order.
        after = connection.execute(f'SELECT {projection} FROM {history}').fetchall()
        if Counter(before) != Counter(after):
            raise ValueError('Gold schema migration rejected: historical content changed')
        if connection.execute('SELECT * FROM bmw_analytics.main.current_gold_run').fetchall() != active_before:
            raise ValueError('Gold schema migration rejected: active run changed')
        if Counter(connection.execute(f'SELECT * FROM {visible}').fetchall()) != Counter(visible_before):
            raise ValueError('Gold schema migration rejected: visible content changed')
        connection.execute('COMMIT')
    except Exception:
        connection.execute('ROLLBACK')
        raise
    logger.info('Gold history migration committed; active run and public columns preserved')
    return missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Apply the verified additive migration; otherwise inspect only.')
    args = parser.parse_args()
    configure_logging()
    run = get_current_run(PROJECT_DIR / 'data/gold')
    if not os.environ.get('motherduck_token'):
        os.environ['motherduck_token'] = getpass.getpass('Token MotherDuck : ').strip()
    with log_operation(logger, 'Migrate MotherDuck Gold history schema',
                       run_id=run.name, stage='motherduck_migration', source_id='-'):
        with duckdb.connect('md:bmw_analytics') as connection:
            migrate_schema(connection, run / 'race_car_summary.parquet', apply=args.apply)


if __name__ == '__main__':
    main()
