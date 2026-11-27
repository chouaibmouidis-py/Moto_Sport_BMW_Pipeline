"""Storage adapters for the Bronze format comparisons."""

from functools import partial

from moto_sport_bmw_pipeline import bronze, bronze_storage, source_loading


def read_bronze(connection, path, *, json_columns=()):
    if path.suffix != ".vortex":
        return bronze_storage.read_bronze(connection, path, json_columns=json_columns)
    connection.execute("LOAD vortex")
    saved = connection.sql("SELECT * FROM read_vortex(?)", params=[str(path)])
    return bronze_storage.restore_json_columns(saved, json_columns)


def read_vortex_classification(connection, path):
    return read_bronze(
        connection, path, json_columns=("session", "fastest_lap", "classification")
    )


def _write_vortex(connection, document, view, path):
    connection.execute("LOAD vortex")
    connection.execute(f'COPY "{view}" TO ? (FORMAT vortex)', [str(path)])


def publish_bronze(connection, document, path, **options):
    if path.suffix != ".vortex":
        return bronze_storage.publish_bronze(connection, document, path, **options)
    return bronze_storage.publish_candidate(
        connection, document, path, write=_write_vortex, read=read_bronze, **options
    )


build_classification_document = partial(
    bronze.build_classification_document, _publish=publish_bronze
)
build_classification_csv = partial(
    bronze.build_classification_csv, _publish=publish_bronze
)
build_document = partial(bronze.build_document, _publish=publish_bronze)
build_pdf_pit_stop_bronze = partial(
    bronze.build_pdf_pit_stop_bronze, _publish=publish_bronze
)

load_classification_bronze = partial(
    source_loading.load_classification_bronze, _read=read_bronze
)
load_classification_csv_bronze = partial(
    source_loading.load_classification_csv_bronze, _read=read_bronze
)
load_pit_stop_file = partial(source_loading.load_pit_stop_file, _read=read_bronze)
load_pdf_pit_stop_bronze = partial(
    source_loading.load_pdf_pit_stop_bronze, _read=read_bronze
)
