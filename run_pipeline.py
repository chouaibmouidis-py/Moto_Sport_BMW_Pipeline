import subprocess
import sys
from pathlib import Path
import json

from manifest_validation import validate_unique_source_ids


PROJECT_DIR = Path(__file__).resolve().parent


def main() -> None:
    manifest_path = PROJECT_DIR / "config" / "sources.json"

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    validate_unique_source_ids(manifest["documents"])
    scripts = [
        "inspect_manifest.py",
        "build_bronze.py",
        "inspect_classification.py",
        "build_classification_bronze.py",
        "analyze_bronze.py",
    ]

    for script in scripts:
        print(f"Starting: {script}", flush=True)

        subprocess.run(
            [sys.executable, str(PROJECT_DIR / script)],
            cwd=PROJECT_DIR,
            check=True,
        )

        print(f"Completed: {script}", flush=True)

    print("Pipeline completed successfully.")


if __name__ == "__main__":
    main()
