import hashlib
import json
from unittest.mock import Mock

import pytest

from moto_sport_bmw_pipeline import bronze, pipeline


@pytest.mark.parametrize(
    "role, source_format, suffix",
    [
        ("classification", "json", "parquet"),
        ("pit_stops", "json", "parquet"),
        ("classification", "csv", "parquet"),
        ("pit_stops", "pdf", "parquet"),
    ],
)
def test_bronze_path_matches_current_storage_contract(
    tmp_path, role, source_format, suffix
):
    source = {"source_id": "source-a", "document_type": role, "format": source_format}
    assert bronze.bronze_document_path(tmp_path, source) == (
        tmp_path / "data/bronze/source-a" / f"document.{suffix}"
    )


@pytest.mark.parametrize("change_bronze", [False, True])
def test_processing_fingerprints_actual_bronze_inputs(
    tmp_path, monkeypatch, change_bronze
):
    documents = [
        dict(
            source_id=role,
            document_type=role,
            format="json",
            championship="test",
            season=2024,
            event_id="test",
            session_id="race",
        )
        for role in ("classification", "pit_stops")
    ]
    expected_hashes = {}
    for source, suffix, content in zip(
        documents, ("parquet", "parquet"), (b"classification fixture", b"pit fixture")
    ):
        path = tmp_path / "data/bronze" / source["source_id"] / f"document.{suffix}"
        path.parent.mkdir(parents=True)
        path.write_bytes(content)
        expected_hashes[path.relative_to(tmp_path).as_posix()] = hashlib.sha256(
            content
        ).hexdigest()

    extension_directory = tmp_path / "extensions"

    def fake_candidate(root, *, documents, activate, verbose, extension_directory):
        # Stub transformation outputs: this test exercises paths/hashes, not file readers.
        candidate = root / "data/runs/test-candidate"
        for relative in (
            "marts/race_car_summary.parquet",
            "silver/classification.parquet",
            "silver/car_entries.parquet",
        ):
            output = candidate / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"output fixture")
        if change_bronze:
            (root / "data/bronze/classification/document.parquet").write_bytes(
                b"changed"
            )
        return candidate

    candidate_spy = Mock(side_effect=fake_candidate)
    activation = Mock()
    monkeypatch.setattr(pipeline, "build_candidate_run", candidate_spy)
    monkeypatch.setattr(pipeline, "activate_run", activation)

    if change_bronze:
        with pytest.raises(
            ValueError,
            match="Processing rejected: Bronze input changed: .*document.parquet",
        ):
            pipeline.build_processing_run(
                tmp_path, documents, extension_directory=extension_directory
            )
        activation.assert_not_called()
    else:
        run = pipeline.build_processing_run(
            tmp_path, documents, extension_directory=extension_directory
        )
        manifest = json.loads((run / "outputs.json").read_text(encoding="utf-8"))
        assert manifest["bronze_hashes"] == expected_hashes
        activation.assert_called_once_with(
            run, required_outputs=("sources.json", "outputs.json")
        )

    candidate_spy.assert_called_once_with(
        tmp_path,
        documents=documents,
        activate=False,
        verbose=False,
        extension_directory=extension_directory,
    )
