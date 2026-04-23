import json
from datetime import datetime
from pathlib import Path

from melody_tab.output import create_run_output_dir, sanitize_title, write_run_meta


def test_title_sanitization_removes_unsafe_chars_and_normalizes_whitespace():
    title = 'Ado: "Odo" / Live? 2024*'
    assert sanitize_title(title) == "Ado_Odo_Live_2024"


def test_title_sanitization_truncates_long_values():
    long_title = "Very Long Title " * 20
    safe = sanitize_title(long_title, max_length=40)
    assert len(safe) <= 40
    assert "__" not in safe
    assert safe.endswith("_") is False


def test_timestamped_run_directory_creation(tmp_path: Path):
    run_dir = create_run_output_dir(
        tmp_path,
        "Ado_Odo",
        timestamp=datetime(2026, 4, 23, 12, 5, 12),
    )
    assert run_dir.name == "20260423_120512__Ado_Odo"
    assert run_dir.exists()


def test_write_run_meta_json(tmp_path: Path):
    run_dir = create_run_output_dir(tmp_path, "song", timestamp=datetime(2026, 4, 23, 12, 5, 12))
    meta = {
        "timestamp": "2026-04-23T12:05:12",
        "source_url": "https://youtube.com/watch?v=abc",
        "source_title": "Song",
        "safe_title": "Song",
        "output_dir": str(run_dir),
        "cli_parameters": {"out_dir": "output"},
    }
    meta_path = write_run_meta(run_dir, meta)
    loaded = json.loads(meta_path.read_text(encoding="utf-8"))

    assert meta_path.name == "run_meta.json"
    assert loaded["safe_title"] == "Song"
    assert loaded["output_dir"] == str(run_dir)
