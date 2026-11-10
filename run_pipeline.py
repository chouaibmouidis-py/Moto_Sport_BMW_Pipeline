import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent


def main() -> None:
    scripts = [
        "inspect_manifest.py",
        "build_bronze.py",
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
