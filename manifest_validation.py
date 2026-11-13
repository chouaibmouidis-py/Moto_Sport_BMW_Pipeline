"""Preserve the historical import of validate_unique_source_ids.

Manifest identifier validation lives in src/moto_sport_bmw_pipeline/manifest.py.
This module only re-exports it; edit the implementation there to change behavior.
"""

from moto_sport_bmw_pipeline.manifest import validate_unique_source_ids
