"""Helpers for organizing per-run output artifacts."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

MAX_SAFE_TITLE_LENGTH = 80
_UNSAFE_FS_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_WHITESPACE_RE = re.compile(r"\s+")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


def sanitize_title(title: str | None, *, max_length: int = MAX_SAFE_TITLE_LENGTH) -> str:
    """Convert source title into a filesystem-safe, readable slug-like value."""
    if not title:
        return "untitled"

    safe = _UNSAFE_FS_CHARS_RE.sub(" ", title).strip()
    safe = _WHITESPACE_RE.sub("_", safe)
    safe = _MULTI_UNDERSCORE_RE.sub("_", safe).strip("._- ")

    if not safe:
        return "untitled"
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip("._- ")
    return safe or "untitled"


def create_run_output_dir(parent_dir: Path, safe_title: str, *, timestamp: datetime | None = None) -> Path:
    """Create timestamp+title run directory under the supplied parent directory."""
    ts = (timestamp or datetime.now()).strftime("%Y%m%d_%H%M%S")
    run_dir = parent_dir / f"{ts}__{safe_title}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_run_meta(out_dir: Path, meta: dict[str, Any]) -> Path:
    """Write run metadata JSON into the run output directory."""
    out_path = out_dir / "run_meta.json"
    out_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
