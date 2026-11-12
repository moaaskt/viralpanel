"""ViralPanel - autonomous viral content pipeline."""

import os
from pathlib import Path
import sys

_venv_bin = str(Path(sys.executable).resolve().parent)
if _venv_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{_venv_bin}{os.pathsep}{os.environ.get('PATH', '')}"

