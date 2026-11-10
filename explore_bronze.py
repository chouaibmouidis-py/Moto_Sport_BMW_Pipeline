import argparse
from pathlib import Path

import duckdb

from download import RAW_DIR, SOURCE_FILENAME


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore the local IMSA JSON with DuckDB SQL.")
    parser.add_argument("path", nargs="?", type=Path, default=Path(RAW_DIR) / SOURCE_FILENAME)
    parser.add_argument(
        "--sql",
        type=Path,
        default=Path(__file__).parent / "sql" / "01_inspect_raw.sql",
        help="Chemin du fichier SQL à exécuter",
    )
    args = parser.parse_args()
    query_path = args.sql
    with duckdb.connect() as connection:
        document = connection.read_json(str(args.path), format="unstructured")
        document.create_view("raw_document")
        print("Root columns:", document.columns)
        result = connection.sql(query_path.read_text(encoding="utf-8"))
        result.show()



if __name__ == "__main__":
    main()
