"""CLI for melody-tab MVP pipeline."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from melody_tab.audio import convert_to_wav, trim_audio
from melody_tab.download import download_audio
from melody_tab.notes import midi_to_note_events, write_notes_file
from melody_tab.tab import write_tab_file
from melody_tab.transcribe import transcribe_wav_to_midi
from melody_tab.utils import setup_logging

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    p = argparse.ArgumentParser(description="Extract melody from YouTube/audio and output MIDI, notes, and guitar TAB.")
    p.add_argument("youtube_url", help="YouTube URL to download and process")
    p.add_argument("--start", type=float, default=None, help="Start seconds for trimming")
    p.add_argument("--end", type=float, default=None, help="End seconds for trimming")
    p.add_argument("--out-dir", default="output", help="Output directory (default: output)")
    p.add_argument("--keep-intermediate", action="store_true", help="Keep downloaded and intermediate wav files")
    p.add_argument("--japanese-solfege", action="store_true", help="Include ドレミ naming in notes.txt")
    p.add_argument("--lowest-fret", type=int, default=0, help="Lowest allowed fret for tab generation")
    p.add_argument("--highest-fret", type=int, default=20, help="Highest allowed fret for tab generation")
    return p


def run_pipeline(args: argparse.Namespace) -> int:
    """Run end-to-end transcription pipeline."""
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.start is not None and args.end is not None and args.start >= args.end:
        raise ValueError("Invalid trim range: --start must be less than --end")
    if args.lowest_fret > args.highest_fret:
        raise ValueError("--lowest-fret cannot be greater than --highest-fret")

    raw_audio = out_dir / "source_audio"
    raw_wav = out_dir / "source.wav"
    trimmed_wav = out_dir / "source_trimmed.wav"
    midi_path = out_dir / "melody.mid"
    notes_path = out_dir / "notes.txt"
    tab_path = out_dir / "tab.txt"

    downloaded = download_audio(args.youtube_url, out_dir=out_dir, basename=raw_audio.name)
    wav = convert_to_wav(downloaded, raw_wav)
    prepared = trim_audio(wav, trimmed_wav, start=args.start, end=args.end)
    transcribe_wav_to_midi(prepared, midi_path)

    events = midi_to_note_events(midi_path)
    if not events:
        raise RuntimeError("No notes were detected in transcription. Try a clearer melody or narrower clip.")

    write_notes_file(events, notes_path, japanese_solfege=args.japanese_solfege)
    write_tab_file(events, tab_path, lowest_fret=args.lowest_fret, highest_fret=args.highest_fret)

    LOGGER.info("Done. Wrote files:\n- %s\n- %s\n- %s", midi_path, notes_path, tab_path)

    if not args.keep_intermediate:
        if downloaded.exists() and downloaded != midi_path:
            downloaded.unlink(missing_ok=True)
        if raw_wav.exists() and raw_wav != prepared:
            raw_wav.unlink(missing_ok=True)
        if trimmed_wav.exists() and prepared != trimmed_wav:
            trimmed_wav.unlink(missing_ok=True)

    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return run_pipeline(args)
    except Exception as exc:
        LOGGER.error("melody-tab failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
