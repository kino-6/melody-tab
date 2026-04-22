"""Transcription backend wrappers."""

from __future__ import annotations

import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def transcribe_wav_to_midi(input_wav: Path, output_midi: Path) -> Path:
    """Transcribe WAV to MIDI using Spotify Basic Pitch.

    Import is local to avoid forcing heavy dependency for lightweight unit tests.
    """
    try:
        from basic_pitch.inference import predict_and_save
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "basic-pitch is not installed or failed to import. Install dependency and retry."
        ) from exc

    output_midi.parent.mkdir(parents=True, exist_ok=True)
    output_dir = output_midi.parent

    LOGGER.info("Running Basic Pitch transcription...")
    predict_and_save(
        audio_path_list=[str(input_wav)],
        output_directory=str(output_dir),
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False,
    )

    inferred = output_dir / f"{input_wav.stem}_basic_pitch.mid"
    if not inferred.exists():
        # fallback: first midi in directory generated recently
        mids = sorted(output_dir.glob("*.mid"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not mids:
            raise RuntimeError("Basic Pitch finished, but no MIDI output was generated.")
        inferred = mids[0]

    inferred.replace(output_midi)
    LOGGER.info("Generated MIDI: %s", output_midi)
    return output_midi
