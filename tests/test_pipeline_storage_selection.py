from pathlib import Path
from unittest.mock import Mock

import pytest
from vortex_support import VORTEX_EXTENSION_DIRECTORY

from moto_sport_bmw_pipeline import pipeline


@pytest.mark.parametrize(
    "extension_directory", [None, Path(str(VORTEX_EXTENSION_DIRECTORY))]
)
def test_candidate_requests_vortex_classification(
    tmp_path, monkeypatch, extension_directory
):

    sources = [
        {
            "source_id": "source-a",
            "enabled": True,
            "document_type": "classification",
            "format": "json",
        }
    ]

    sql_directory = tmp_path / "sql"
    sql_directory.mkdir()
    (sql_directory / "21_create_duration_parser.sql").write_text(
        "SELECT 1", encoding="utf-8"
    )

    for name in (
        "load_source_sessions",
        "build_source_pairs",
        "load_pit_stop_bronze",
        "transform_sessions",
        "transform_driver_entries",
        "transform_car_entries",
        "transform_pit_stops",
        "build_session_quality",
        "build_duration_reports",
        "build_enriched_stops",
    ):
        monkeypatch.setattr(pipeline, name, Mock())

    for name in ("transform_driver_entries", "transform_car_entries"):
        transform = getattr(pipeline, name)
        transform.return_value.count.return_value.fetchone.return_value = (0,)

    original_connect = pipeline.duckdb.connect
    connection_configs = []

    def connect_with_recorded_config(*args, **kwargs):
        connection_configs.append(kwargs["config"])
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(pipeline.duckdb, "connect", connect_with_recorded_config)
    calls = []

    def observe_loading(connection, selected_sources, project_directory, **kwargs):
        calls.append((selected_sources, project_directory, kwargs))
        raise RuntimeError("Stop after loading request")

    monkeypatch.setattr(
        pipeline,
        "load_classification_sources",
        observe_loading,
    )

    with pytest.raises(RuntimeError, match="Stop after loading request"):
        pipeline.build_candidate_run(
            tmp_path,
            documents=sources,
            activate=False,
            extension_directory=extension_directory,
        )

    assert calls == [(sources, tmp_path, {})]
    assert connection_configs == [
        {}
        if extension_directory is None
        else {"extension_directory": str(extension_directory)}
    ]
