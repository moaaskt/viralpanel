import shutil
import time
from pathlib import Path

from viralpanel.config import get_settings


class StorageManager:
    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir or get_settings().storage_dir).resolve()

    @property
    def runs_dir(self) -> Path:
        return self.base_dir / "runs"

    def _safe(self, path: Path) -> Path:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.base_dir):
            raise ValueError(f"path escapes storage dir: {path}")
        return resolved

    def get_run_dir(self, run_id: str) -> Path:
        run_dir = self._safe(self.runs_dir / run_id / "assets")
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def save_bytes(self, run_id: str, filename: str, data: bytes) -> Path:
        target = self._safe(self.get_run_dir(run_id) / filename)
        target.write_bytes(data)
        return target

    def cleanup_old_runs(self, days_retention: int = 7) -> int:
        if not self.runs_dir.exists():
            return 0
        cutoff = time.time() - days_retention * 86400
        removed = 0
        for d in self.runs_dir.iterdir():
            if d.is_dir() and d.stat().st_mtime < cutoff:
                shutil.rmtree(d)
                removed += 1
        return removed
