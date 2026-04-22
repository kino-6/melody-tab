"""Transcription backend wrappers."""

from __future__ import annotations

import logging
from pathlib import Path
import subprocess

LOGGER = logging.getLogger(__name__)


def transcribe_wav_to_midi(input_wav: Path, output_midi: Path) -> Path:
    """Transcribe WAV to MIDI using the Basic Pitch CLI."""
    output_midi.parent.mkdir(parents=True, exist_ok=True)
    output_dir = output_midi.parent

    command = [
        "basic-pitch",
        "--save-midi",
        "--model-serialization",
        "onnx",
        str(output_dir),
        str(input_wav),
    ]
    LOGGER.info("Starting Basic Pitch transcription for %s", input_wav)
    LOGGER.info("Executing command: %s", " ".join(command))

    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        LOGGER.error("Basic Pitch transcription failed with exit code %s", result.returncode)
        LOGGER.error("Basic Pitch stdout:\n%s", result.stdout)
        LOGGER.error("Basic Pitch stderr:\n%s", result.stderr)
        raise RuntimeError(
            "Basic Pitch CLI transcription failed. Check logs for full stdout/stderr."
        )

    LOGGER.info("Finished Basic Pitch transcription for %s", input_wav)

    inferred = output_dir / f"{input_wav.stem}_basic_pitch.mid"
    if not inferred.exists():
        # fallback: first MIDI in directory generated recently
        mids = sorted(output_dir.glob("*.mid"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not mids:
            raise RuntimeError("Basic Pitch finished, but no MIDI output was generated.")

        # Prefer expected naming patterns for robust detection.
        stem_matches = [m for m in mids if m.stem.startswith(input_wav.stem)]
        inferred = stem_matches[0] if stem_matches else mids[0]

    inferred.replace(output_midi)
    LOGGER.info("Output MIDI path: %s", output_midi)
    return output_midi
