from viralpanel.media.downloader import MockMediaDownloader
from viralpanel.storage import StorageManager


def test_mock_download_and_extract_isolated_by_run(tmp_path):
    dl = MockMediaDownloader(storage=StorageManager(tmp_path))
    video, audio = dl.fetch("run-123", "https://www.tiktok.com/@x/video/1")
    assert video.exists() and audio.exists()
    assert video.parent == (tmp_path / "runs" / "run-123" / "source").resolve()
    assert audio.suffix == ".wav"


def test_source_dir_rejects_traversal(tmp_path):
    dl = MockMediaDownloader(storage=StorageManager(tmp_path))
    try:
        dl.source_dir("../../etc")
    except ValueError:
        return
    raise AssertionError("traversal não bloqueado")

