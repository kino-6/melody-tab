"""YouTube audio download/extraction using yt-dlp."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from melody_tab.utils import run_command

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceMetadata:
    """Relevant source metadata for output organization and tracing."""

    source_url: str
    source_title: str | None = None


def fetch_source_metadata(url: str) -> SourceMetadata:
    """Fetch source metadata from yt-dlp JSON output, if available."""
    cmd = ["yt-dlp", "--dump-single-json", "--no-playlist", "--skip-download", url]
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    except FileNotFoundError:
        LOGGER.warning("yt-dlp is not installed; proceeding without source title metadata.")
        return SourceMetadata(source_url=url)
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip() or "unknown yt-dlp metadata error"
        LOGGER.warning("Failed to fetch source metadata: %s", details)
        return SourceMetadata(source_url=url)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        LOGGER.warning("Unable to parse yt-dlp metadata JSON; proceeding without source title.")
        return SourceMetadata(source_url=url)

    title = str(data.get("title")).strip() if data.get("title") else None
    return SourceMetadata(source_url=url, source_title=title or None)


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
