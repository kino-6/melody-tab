"""CLI for melody-tab MVP pipeline."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from melody_tab.audio import convert_to_wav, trim_audio
from melody_tab.download import download_audio, fetch_source_metadata
from melody_tab.melody import MelodyConfig, extract_melody, format_melody_debug
from melody_tab.notes import midi_to_note_events, write_note_events_midi, write_notes_file
from melody_tab.output import create_run_output_dir, sanitize_title, write_run_meta
from melody_tab.tab import TabConfig, write_tab_file
from melody_tab.tab_parse import parse_tab_file
from melody_tab.tab_to_midi import tab_to_midi_pipeline
from melody_tab.transcribe import transcribe_wav_to_midi
from melody_tab.utils import setup_logging

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    p = argparse.ArgumentParser(description="Extract melody from YouTube/audio and output MIDI, notes, and guitar TAB.")
    p.add_argument("youtube_url", nargs="?", help="YouTube URL to download and process")
    p.add_argument("--start", type=float, default=None, help="Start seconds for trimming")
    p.add_argument("--end", type=float, default=None, help="End seconds for trimming")
    p.add_argument("--out-dir", default="output", help="Output directory (default: output)")
    p.add_argument("--keep-intermediate", action="store_true", help="Keep downloaded and intermediate wav files")
    p.add_argument("--japanese-solfege", action="store_true", help="Include ドレミ naming in notes files")
    p.add_argument("--lowest-fret", type=int, default=0, help="Lowest allowed fret for tab generation")
    p.add_argument("--highest-fret", type=int, default=20, help="Highest allowed fret for tab generation")

    p.add_argument("--tab-to-midi", default=None, help="Convert an existing tab.txt into a MIDI preview")
    p.add_argument("--out", default=None, help="Output MIDI path for --tab-to-midi mode")
    p.add_argument("--step-beats", type=float, default=0.5, help="Step duration in beats for TAB-to-MIDI mode")
    p.add_argument("--tempo", type=float, default=120.0, help="Tempo for TAB-to-MIDI mode")
    p.add_argument("--timing-from-notes", default=None, help="Use notes_melody.txt timing for TAB-to-MIDI alignment")
    p.add_argument("--compare-with-notes", default=None, help="Compare tab-derived notes to notes_melody.txt")

    p.add_argument("--melody-mode", choices=["highest", "duration", "balanced"], default="balanced")
    p.add_argument("--min-note-ms", type=float, default=90.0, help="Minimum note length to keep")
    p.add_argument("--preferred-fret-max", type=int, default=12, help="Preferred upper fret (soft penalty after this)")
    p.add_argument("--max-jump-semitones", type=int, default=12, help="Pitch jump threshold before continuity penalty")
    p.add_argument("--octave-shift-outliers", action="store_true", help="Try octave-shifting out-of-range notes")
    p.add_argument("--debug-melody", action="store_true", help="Write melody_debug.txt with scoring details")

    p.add_argument("--write-melody-midi", action=argparse.BooleanOptionalAction, default=True, help="Write melody.mid")
    p.add_argument(
        "--write-tab-preview-midi",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write tab_preview.mid from tab.txt",
    )
    p.add_argument(
        "--write-compare-report",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write compare_melody_vs_tab.txt report",
    )
    return p


def run_pipeline(args: argparse.Namespace) -> int:
    """Run end-to-end transcription pipeline."""
    out_parent_dir = Path(args.out_dir).resolve()
    out_parent_dir.mkdir(parents=True, exist_ok=True)

    if args.start is not None and args.end is not None and args.start >= args.end:
        raise ValueError("Invalid trim range: --start must be less than --end")
    if args.lowest_fret > args.highest_fret:
        raise ValueError("--lowest-fret cannot be greater than --highest-fret")

    source_meta = fetch_source_metadata(args.youtube_url)
    safe_title = sanitize_title(source_meta.source_title)
    run_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    out_dir = create_run_output_dir(out_parent_dir, safe_title)

    LOGGER.info("Source title: %s", source_meta.source_title or "(unknown)")
    LOGGER.info("Run output directory: %s", out_dir)

    raw_audio = out_dir / "source_audio"
    raw_wav = out_dir / "source.wav"
    trimmed_wav = out_dir / "source_trimmed.wav"

    raw_midi_path = out_dir / "raw.mid"
    melody_midi_path = out_dir / "melody.mid"
    notes_raw_path = out_dir / "notes_raw.txt"
    notes_melody_path = out_dir / "notes_melody.txt"
    notes_compat_path = out_dir / "notes.txt"
    tab_path = out_dir / "tab.txt"
    tab_preview_path = out_dir / "tab_preview.mid"
    compare_path = out_dir / "compare_melody_vs_tab.txt"
    debug_path = out_dir / "melody_debug.txt"
    run_meta_path = out_dir / "run_meta.json"

    run_meta: dict[str, object] = {
        "timestamp": run_timestamp,
        "source_url": source_meta.source_url,
        "source_title": source_meta.source_title,
        "safe_title": safe_title,
        "output_dir": str(out_dir),
        "cli_parameters": vars(args),
        "trim_range": (
            {"start": args.start, "end": args.end}
            if args.start is not None or args.end is not None
            else None
        ),
        "melody_settings": {
            "mode": args.melody_mode,
            "min_note_ms": args.min_note_ms,
            "max_jump_semitones": args.max_jump_semitones,
            "octave_shift_outliers": args.octave_shift_outliers,
            "debug_melody": args.debug_melody,
            "write_melody_midi": args.write_melody_midi,
        },
        "tab_settings": {
            "lowest_fret": args.lowest_fret,
            "preferred_fret_max": args.preferred_fret_max,
            "highest_fret": args.highest_fret,
            "write_tab_preview_midi": args.write_tab_preview_midi,
            "write_compare_report": args.write_compare_report,
            "tempo": args.tempo,
            "step_beats": args.step_beats,
        },
    }

    downloaded = download_audio(args.youtube_url, out_dir=out_dir, basename=raw_audio.name)
    wav = convert_to_wav(downloaded, raw_wav)
    prepared = trim_audio(wav, trimmed_wav, start=args.start, end=args.end)
    transcribe_wav_to_midi(prepared, raw_midi_path)

    raw_events = midi_to_note_events(raw_midi_path)
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
    if args.write_melody_midi:
        write_note_events_midi(melody_events, melody_midi_path)

    tab_cfg = TabConfig(
        lowest_fret=args.lowest_fret,
        highest_fret=args.highest_fret,
        preferred_fret_max=args.preferred_fret_max,
        octave_shift_outliers=args.octave_shift_outliers,
    )
    _, tab_stats = write_tab_file(melody_events, tab_path, config=tab_cfg, source=args.youtube_url)
    tab_events = parse_tab_file(tab_path)

    preview_result = None
    if args.write_tab_preview_midi:
        preview_result = tab_to_midi_pipeline(
            tab_path=tab_path,
            out_path=tab_preview_path,
            step_beats=args.step_beats,
            tempo=args.tempo,
            timing_from_notes=notes_melody_path,
            compare_with_notes=notes_melody_path if args.write_compare_report else None,
            comparison_out=compare_path,
        )

    if args.debug_melody:
        debug_path.write_text(format_melody_debug(decisions, cleanup_debug), encoding="utf-8")

    artifacts = {
        "raw_midi": str(raw_midi_path),
        "notes_raw": str(notes_raw_path),
        "notes_melody": str(notes_melody_path),
        "notes_compat": str(notes_compat_path),
        "tab": str(tab_path),
        "melody_midi": str(melody_midi_path) if args.write_melody_midi else None,
        "tab_preview_midi": str(tab_preview_path) if args.write_tab_preview_midi else None,
        "compare_report": str(compare_path) if args.write_tab_preview_midi and args.write_compare_report else None,
        "melody_debug": str(debug_path) if args.debug_melody else None,
    }
    run_meta["artifacts"] = artifacts
    write_run_meta(out_dir, run_meta)

    LOGGER.info(
        (
            "Stage summary: raw notes parsed=%d | melody notes selected=%d | tab notes emitted=%d | "
            "preview MIDI notes emitted=%d"
        ),
        len(raw_events),
        len(melody_events),
        len(tab_events),
        preview_result.preview_note_count if preview_result else 0,
    )
    LOGGER.info(
        (
            "Verification stats: raw=%d melody=%d tab-events=%d dropped=%d octave-shifted=%d "
            "(melody-shift=%d tab-shift=%d)"
        ),
        len(raw_events),
        len(melody_events),
        len(tab_events),
        tab_stats.dropped_notes,
        melody_stats.octave_shifted + tab_stats.octave_shifted,
        melody_stats.octave_shifted,
        tab_stats.octave_shifted,
    )
    LOGGER.info(
        "Done. Wrote files:\n- %s\n- %s\n- %s\n- %s\n- %s\n- %s%s%s\n- %s",
        raw_midi_path,
        notes_raw_path,
        melody_midi_path if args.write_melody_midi else "(skipped melody.mid)",
        notes_melody_path,
        tab_path,
        tab_preview_path if args.write_tab_preview_midi else "(skipped tab_preview.mid)",
        f"\n- {compare_path}" if args.write_tab_preview_midi and args.write_compare_report else "",
        f"\n- {debug_path}" if args.debug_melody else "",
        run_meta_path,
    )

    if not args.keep_intermediate:
        if downloaded.exists() and downloaded != raw_midi_path:
            downloaded.unlink(missing_ok=True)
        if raw_wav.exists() and raw_wav != prepared:
            raw_wav.unlink(missing_ok=True)
        if trimmed_wav.exists() and prepared != trimmed_wav:
            trimmed_wav.unlink(missing_ok=True)

    return 0


def run_tab_to_midi_mode(args: argparse.Namespace) -> int:
    """Run TAB->MIDI verification/export mode."""
    tab_path = Path(args.tab_to_midi).resolve()
    if not tab_path.exists():
        raise FileNotFoundError(f"TAB file not found: {tab_path}")

    out_path = Path(args.out).resolve() if args.out else tab_path.with_name("preview.mid")
    timing_path = Path(args.timing_from_notes).resolve() if args.timing_from_notes else None
    compare_path = Path(args.compare_with_notes).resolve() if args.compare_with_notes else None

    result = tab_to_midi_pipeline(
        tab_path=tab_path,
        out_path=out_path,
        step_beats=args.step_beats,
        tempo=args.tempo,
        timing_from_notes=timing_path,
        compare_with_notes=compare_path,
    )

    LOGGER.info(
        "TAB-to-MIDI complete. Wrote files:\n- %s\n- %s%s",
        result.midi_path,
        result.debug_path,
        f"\n- {result.comparison_path}" if result.comparison_path else "",
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.tab_to_midi:
            return run_tab_to_midi_mode(args)
        if not args.youtube_url:
            parser.error("youtube_url is required unless --tab-to-midi is used")
        return run_pipeline(args)
    except Exception as exc:
        LOGGER.error("melody-tab failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
