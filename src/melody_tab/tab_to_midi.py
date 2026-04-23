"""TAB-to-MIDI conversion and comparison helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import re

import pretty_midi

from melody_tab.tab_parse import ParsedTabEvent, parse_tab_file

NOTES_LINE_RE = re.compile(r"midi=(?P<midi>-?\d+),\s*start=(?P<start>\d+(?:\.\d+)?),\s*dur=(?P<dur>\d+(?:\.\d+)?)")


@dataclass(slots=True)
class TimedNote:
    midi: int
    start: float
    duration: float


@dataclass(slots=True)
class ComparisonResult:
    tab_note_count: int
    melody_note_count: int
    pitch_mismatches: int
    octave_mismatches: int
    missing_notes: int
    extra_notes: int


@dataclass(slots=True)
class TabToMidiOutput:
    midi_path: Path
    debug_path: Path
    comparison_path: Path | None
    preview_note_count: int


def load_notes_timing(notes_path: Path) -> list[TimedNote]:
    """Parse notes_melody.txt style rows into timed notes."""
    out: list[TimedNote] = []
    for line in notes_path.read_text(encoding="utf-8").splitlines():
        m = NOTES_LINE_RE.search(line)
        if not m:
            continue
        out.append(
            TimedNote(
                midi=int(m.group("midi")),
                start=float(m.group("start")),
                duration=max(0.01, float(m.group("dur"))),
            )
        )
    return out


def events_by_column(events: list[ParsedTabEvent]) -> list[tuple[int, list[ParsedTabEvent]]]:
    grouped: dict[int, list[ParsedTabEvent]] = defaultdict(list)
    for event in events:
        grouped[event.column].append(event)
    cols = sorted(grouped)
    return [(c, sorted(grouped[c], key=lambda ev: ev.string_index)) for c in cols]


def tab_events_to_timed_notes(
    events: list[ParsedTabEvent],
    *,
    tempo: float = 120.0,
    step_beats: float = 0.5,
    timing_notes: list[TimedNote] | None = None,
) -> list[TimedNote]:
    """Turn parsed TAB events into timed notes."""
    by_col = events_by_column(events)
    if not by_col:
        return []

    step_seconds = 60.0 / tempo * step_beats
    timed: list[TimedNote] = []

    for idx, (_, col_events) in enumerate(by_col):
        if timing_notes and idx < len(timing_notes):
            start = timing_notes[idx].start
            dur = timing_notes[idx].duration
        else:
            start = idx * step_seconds
            dur = step_seconds

        for event in col_events:
            timed.append(TimedNote(midi=event.midi, start=start, duration=dur))

    timed.sort(key=lambda n: (n.start, n.midi))
    return timed


def write_debug_notes(events: list[ParsedTabEvent], output_path: Path) -> Path:
    lines = ["string\tfret\tmidi\tpitch\tcolumn"]
    for ev in sorted(events, key=lambda x: (x.column, x.string_index)):
        lines.append(
            f"{ev.string_number}\t{ev.fret}\t{ev.midi}\t{pretty_midi.note_number_to_name(ev.midi)}\t{ev.column}"
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def write_midi(notes: list[TimedNote], output_path: Path, *, tempo: float = 120.0) -> Path:
    midi = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    instrument = pretty_midi.Instrument(program=24, name="TAB Preview Guitar")
    for n in notes:
        instrument.notes.append(
            pretty_midi.Note(
                velocity=96,
                pitch=n.midi,
                start=float(n.start),
                end=float(n.start + max(0.01, n.duration)),
            )
        )
    midi.instruments.append(instrument)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(output_path))
    return output_path


def compare_melody_to_tab(tab_notes: list[TimedNote], melody_notes: list[TimedNote]) -> ComparisonResult:
    tab_seq = [n.midi for n in sorted(tab_notes, key=lambda x: (x.start, x.midi))]
    mel_seq = [n.midi for n in sorted(melody_notes, key=lambda x: (x.start, x.midi))]

    zipped = list(zip(tab_seq, mel_seq))
    pitch_mismatches = sum(1 for t, m in zipped if t % 12 != m % 12)
    octave_mismatches = sum(1 for t, m in zipped if t != m and t % 12 == m % 12)

    tab_counts = Counter(tab_seq)
    mel_counts = Counter(mel_seq)
    missing_notes = sum(max(0, mel_counts[p] - tab_counts[p]) for p in mel_counts)
    extra_notes = sum(max(0, tab_counts[p] - mel_counts[p]) for p in tab_counts)

    return ComparisonResult(
        tab_note_count=len(tab_seq),
        melody_note_count=len(mel_seq),
        pitch_mismatches=pitch_mismatches,
        octave_mismatches=octave_mismatches,
        missing_notes=missing_notes,
        extra_notes=extra_notes,
    )


def format_comparison(result: ComparisonResult) -> str:
    return "\n".join(
        [
            "# TAB vs melody comparison",
            f"tab-note-count: {result.tab_note_count}",
            f"melody-note-count: {result.melody_note_count}",
            f"pitch-mismatches: {result.pitch_mismatches}",
            f"octave-mismatches: {result.octave_mismatches}",
            f"missing-notes: {result.missing_notes}",
            f"extra-notes: {result.extra_notes}",
        ]
    )


def tab_to_midi_pipeline(
    *,
    tab_path: Path,
    out_path: Path,
    step_beats: float = 0.5,
    tempo: float = 120.0,
    timing_from_notes: Path | None = None,
    debug_path: Path | None = None,
    compare_with_notes: Path | None = None,
    comparison_out: Path | None = None,
) -> TabToMidiOutput:
    events = parse_tab_file(tab_path)
    timings = load_notes_timing(timing_from_notes) if timing_from_notes else None
    timed_notes = tab_events_to_timed_notes(events, tempo=tempo, step_beats=step_beats, timing_notes=timings)

    write_midi(timed_notes, out_path, tempo=tempo)
    debug_file = debug_path or out_path.with_name("tab_parsed_notes.txt")
    write_debug_notes(events, debug_file)

    comparison_file: Path | None = None
    if compare_with_notes:
        melody_notes = load_notes_timing(compare_with_notes)
        result = compare_melody_to_tab(timed_notes, melody_notes)
        comparison_file = comparison_out or out_path.with_name("compare_melody_vs_tab.txt")
        comparison_file.write_text(format_comparison(result), encoding="utf-8")

    return TabToMidiOutput(
        midi_path=out_path,
        debug_path=debug_file,
        comparison_path=comparison_file,
        preview_note_count=len(timed_notes),
    )
