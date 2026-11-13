"""Keep the historical `from silver_writer import publish_silver` import working.

This module re-exports the function; its implementation and validation logic live
in src/moto_sport_bmw_pipeline/parquet_writer.py. Edit that file to change behavior.
"""

from moto_sport_bmw_pipeline.parquet_writer import publish_silver
