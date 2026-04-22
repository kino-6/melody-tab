"""Audio conversion and optional trimming helpers."""

from __future__ import annotations

import logging
from pathlib import Path

from melody_tab.utils import run_command

LOGGER = logging.getLogger(__name__)


def convert_to_wav(input_audio: Path, output_wav: Path) -> Path:
    """Convert arbitrary audio file to mono 44.1kHz wav via ffmpeg."""
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_audio),
        "-ac",
        "1",
        "-ar",
        "44100",
        str(output_wav),
    ]
    LOGGER.info("Converting to WAV via ffmpeg...")
    run_command(cmd, context="ffmpeg wav conversion")
    return output_wav


def trim_audio(input_wav: Path, output_wav: Path, start: float | None, end: float | None) -> Path:
    """Trim wav to [start, end] if requested, using ffmpeg stream copy where possible."""
    if start is None and end is None:
        return input_wav

    if start is not None and start < 0:
        raise ValueError("--start must be >= 0")
    if end is not None and end < 0:
        raise ValueError("--end must be >= 0")
    if start is not None and end is not None and start >= end:
        raise ValueError("Invalid trim range: --start must be less than --end")

    cmd = ["ffmpeg", "-y", "-i", str(input_wav)]
    if start is not None:
        cmd += ["-ss", f"{start}"]
    if end is not None:
        cmd += ["-to", f"{end}"]
    cmd += ["-ac", "1", "-ar", "44100", str(output_wav)]

    LOGGER.info("Trimming audio (start=%s, end=%s)", start, end)
    run_command(cmd, context="ffmpeg trim")
    return output_wav
