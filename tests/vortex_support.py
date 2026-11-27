"""Shared test extension location; installation is explicit and outside pytest."""

import os
import sys
import tempfile
from pathlib import Path

_default_directory = (
    Path("/private/tmp/bmw-vortex-extensions")
    if sys.platform == "darwin"
    else Path(tempfile.gettempdir()) / "bmw-vortex-extensions"
)
VORTEX_EXTENSION_DIRECTORY = Path(
    os.environ.get("BMW_VORTEX_EXTENSION_DIRECTORY", str(_default_directory))
)
