from pathlib import Path
from unittest.mock import Mock

import pytest

from moto_sport_bmw_pipeline import orchestration


@pytest.mark.parametrize("stage", ["bronze", "process"])
def test_stages_forward_extension_directory(tmp_path, monkeypatch, stage):
    source = {"source_id": "source-a"}
    extension_directory = tmp_path / "extensions"
    monkeypatch.setattr(orchestration, "prepare_source", Mock())
    build = Mock()
    process = Mock()
    monkeypatch.setattr(orchestration, "build_source", build)
    monkeypatch.setattr(orchestration, "build_processing_run", process)

    orchestration.run_stages(
        tmp_path,
        [source],
        stage=stage,
        extension_directory=extension_directory,
    )

    if stage == "bronze":
        build.assert_called_once_with(
            tmp_path, source, extension_directory=extension_directory
        )
        process.assert_not_called()
    else:
        process.assert_called_once_with(
            tmp_path, [source], verbose=False, extension_directory=extension_directory
        )
        build.assert_not_called()


def test_cli_forwards_extension_directory(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/sources.json").write_text('{"documents": []}', encoding="utf-8")
    monkeypatch.setattr(orchestration, "configure_logging", Mock())
    monkeypatch.setattr(orchestration, "select_documents", Mock(return_value=[]))
    run = Mock()
    monkeypatch.setattr(orchestration, "run_stages", run)

    orchestration.main(
        ["--stage", "bronze", "--extension-directory", str(tmp_path / "extensions")],
        project_directory=tmp_path,
    )

    assert run.call_args.kwargs["extension_directory"] == Path(tmp_path / "extensions")
