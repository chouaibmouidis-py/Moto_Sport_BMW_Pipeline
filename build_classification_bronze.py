import json
from pathlib import Path
import uuid
import duckdb
from file_integrity import verify_local_file


def build_classification_document(
    source_path: Path,
    output_path: Path,
) -> None:
    with source_path.open("r", encoding="utf-8-sig") as file:
        source_data = json.load(file)
        print("Classification entries:", len(source_data["classification"]))

    if output_path.suffix != ".parquet":
        raise ValueError(f"Unexpected file format {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex
    temporary_path = output_path.with_name(
        f"{output_path.name}.{run_id}.tmp.parquet"
    )

    with duckdb.connect() as connection:
        document = connection.read_json(
            str(source_path),
            format="unstructured",
            columns={
                "session": "JSON",
                "fastest_lap": "JSON",
                "classification": "JSON",
            },
        )

        document.write_parquet(str(temporary_path))

        saved = connection.read_parquet(str(temporary_path))

        rows = saved.project(
            "to_json(session), to_json(fastest_lap), to_json(classification)"
        ).fetchall()

        if len(rows) != 1:
            raise ValueError(
                f"Expected one document, found {len(rows)} rows"
            )

        for column_index, root_name in enumerate(
            ("session", "fastest_lap", "classification")
        ):
            saved_value = json.loads(rows[0][column_index])

            if saved_value != source_data[root_name]:
                raise ValueError(
                    f"Bronze rejected: content differs for {root_name}"
                )

    temporary_path.replace(output_path)
    print("Bronze published:", output_path)

def main() -> None:
    project_directory = Path(__file__).resolve().parent
    manifest_path = project_directory / "config" / "sources.json"

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    selected_sources = select_classification_sources(manifest["documents"])

    for source in selected_sources:
        source_id = source["source_id"]

        raw_directory = project_directory / "data" / "raw" / source_id
        source_path = raw_directory / source["filename"]
        metadata_path = raw_directory / "metadata.json"

        output_path = (
            project_directory
            / "data"
            / "bronze"
            / source_id
            / "document.parquet"
        )

        verify_local_file(source_path, metadata_path)
        build_classification_document(source_path, output_path)

def select_classification_sources(documents):
    selected_souce = []
    for document in documents:
        if document.get("enabled", False) and document["document_type"] == "classification":
            selected_souce.append(document)
    return selected_souce

if __name__ == "__main__":
    main()
