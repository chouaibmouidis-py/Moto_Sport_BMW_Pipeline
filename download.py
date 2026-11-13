"""Preserve historical download imports and the standalone download command.

Download logic lives in src/moto_sport_bmw_pipeline/raw_download.py.
Running this file calls that module's main function; importing it re-exports
the existing functions and constants for callers that still use `download`.
"""

import requests

from moto_sport_bmw_pipeline.raw_download import (
    BASE_URL, RAW_DIR, BRONZE_DIR, SOURCE_FILENAME, download, main,
)


if __name__ == "__main__":
    main()
