import os
import time

import pytest

from viralpanel.storage import StorageManager


def test_run_dir_and_save(tmp_path):
    sm = StorageManager(tmp_path)
    p = sm.save_bytes("run1", "a.bin", b"x")
    assert p.read_bytes() == b"x"
    assert "run1" in str(p)


def test_cleanup(tmp_path):
    sm = StorageManager(tmp_path)
    sm.get_run_dir("old")
    sm.get_run_dir("new")
    old = sm.runs_dir / "old"
    t = time.time() - 10 * 86400
    os.utime(old, (t, t))
    assert sm.cleanup_old_runs(7) == 1
    assert not old.exists() and (sm.runs_dir / "new").exists()


def test_traversal_blocked(tmp_path):
    sm = StorageManager(tmp_path)
    with pytest.raises(ValueError):
        sm.get_run_dir("../../evil")
