"""YouTube audio download/extraction using yt-dlp."""

from __future__ import annotations

import logging
from pathlib import Path

from melody_tab.utils import run_command

LOGGER = logging.getLogger(__name__)


def download_audio(url: str, out_dir: Path, basename: str = "source") -> Path:
    """Download best quality audio for URL into out_dir and return file path.

    Uses yt-dlp to extract audio while preserving local-only workflow.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    output_template = out_dir / f"{basename}.%(ext)s"

    cmd = [
        "yt-dlp",
        "-f",
        "bestaudio/best",
        "-o",
        str(output_template),
        "--no-playlist",
        url,
    ]
    LOGGER.info("Downloading audio with yt-dlp...")
    run_command(cmd, context="yt-dlp download")

    matches = sorted(out_dir.glob(f"{basename}.*"))
    matches = [m for m in matches if m.name != f"{basename}.wav"]
    if not matches:
        raise RuntimeError("yt-dlp completed but no downloaded audio file was found.")
    selected = max(matches, key=lambda p: p.stat().st_size)
    LOGGER.info("Downloaded audio: %s", selected)
    return selected
