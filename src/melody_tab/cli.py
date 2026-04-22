"""CLI for melody-tab MVP pipeline."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from melody_tab.audio import convert_to_wav, trim_audio
from melody_tab.download import download_audio
from melody_tab.melody import MelodyConfig, extract_melody, format_melody_debug
from melody_tab.notes import write_notes_file, midi_to_note_events
from melody_tab.tab import TabConfig, write_tab_file
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
    p.add_argument("--japanese-solfege", action="store_true", help="Include ドレミ naming in notes files")
    p.add_argument("--lowest-fret", type=int, default=0, help="Lowest allowed fret for tab generation")
    p.add_argument("--highest-fret", type=int, default=20, help="Highest allowed fret for tab generation")

    p.add_argument("--melody-mode", choices=["highest", "duration", "balanced"], default="balanced")
    p.add_argument("--min-note-ms", type=float, default=90.0, help="Minimum note length to keep")
    p.add_argument("--preferred-fret-max", type=int, default=12, help="Preferred upper fret (soft penalty after this)")
    p.add_argument("--max-jump-semitones", type=int, default=12, help="Pitch jump threshold before continuity penalty")
    p.add_argument("--octave-shift-outliers", action="store_true", help="Try octave-shifting out-of-range notes")
    p.add_argument("--debug-melody", action="store_true", help="Write melody_debug.txt with scoring details")
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
    notes_raw_path = out_dir / "notes_raw.txt"
    notes_melody_path = out_dir / "notes_melody.txt"
    notes_compat_path = out_dir / "notes.txt"
    tab_path = out_dir / "tab.txt"
    debug_path = out_dir / "melody_debug.txt"

    downloaded = download_audio(args.youtube_url, out_dir=out_dir, basename=raw_audio.name)
    wav = convert_to_wav(downloaded, raw_wav)
    prepared = trim_audio(wav, trimmed_wav, start=args.start, end=args.end)
    transcribe_wav_to_midi(prepared, midi_path)

    raw_events = midi_to_note_events(midi_path)
    if not raw_events:
        raise RuntimeError("No notes were detected in transcription. Try a clearer melody or narrower clip.")

    melody_cfg = MelodyConfig(
        mode=args.melody_mode,
        min_note_ms=args.min_note_ms,
        max_jump_semitones=args.max_jump_semitones,
        octave_shift_outliers=args.octave_shift_outliers,
    )
    melody_events, melody_stats, decisions, cleanup_debug = extract_melody(raw_events, config=melody_cfg)

    if not melody_events:
        raise RuntimeError("No melody notes left after cleanup. Try lowering --min-note-ms or changing --melody-mode.")

    write_notes_file(raw_events, notes_raw_path, japanese_solfege=args.japanese_solfege)
    write_notes_file(melody_events, notes_melody_path, japanese_solfege=args.japanese_solfege)
    write_notes_file(melody_events, notes_compat_path, japanese_solfege=args.japanese_solfege)

    tab_cfg = TabConfig(
        lowest_fret=args.lowest_fret,
        highest_fret=args.highest_fret,
        preferred_fret_max=args.preferred_fret_max,
        octave_shift_outliers=args.octave_shift_outliers,
    )
    _, tab_stats = write_tab_file(melody_events, tab_path, config=tab_cfg, source=args.youtube_url)

    if args.debug_melody:
        debug_path.write_text(format_melody_debug(decisions, cleanup_debug), encoding="utf-8")

    LOGGER.info(
        "Done. Wrote files:\n- %s\n- %s\n- %s\n- %s\nMelody stats: raw=%d dropped_short=%d merged=%d mel_oct_shift=%d mel_drop=%d tab_drop=%d tab_oct_shift=%d",
        midi_path,
        notes_raw_path,
        notes_melody_path,
        tab_path,
        melody_stats.raw_notes,
        melody_stats.dropped_short,
        melody_stats.merged_repeats,
        melody_stats.octave_shifted,
        melody_stats.dropped_unplayable,
        tab_stats.dropped_notes,
        tab_stats.octave_shifted,
    )

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
