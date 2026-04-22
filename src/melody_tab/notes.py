"""MIDI note parsing and text export helpers."""

from __future__ import annotations

from pathlib import Path


from melody_tab.models import NoteEvent

SOLFEGE_JP = {
    "C": "ド",
    "D": "レ",
    "E": "ミ",
    "F": "ファ",
    "G": "ソ",
    "A": "ラ",
    "B": "シ",
}


def midi_to_note_events(midi_path: Path) -> list[NoteEvent]:
    """Parse MIDI file and return sorted note events."""
    import pretty_midi

    midi = pretty_midi.PrettyMIDI(str(midi_path))
    events: list[NoteEvent] = []
    for instrument in midi.instruments:
        for n in instrument.notes:
            name = pretty_midi.note_number_to_name(n.pitch)
            events.append(NoteEvent(midi=n.pitch, name=name, onset=float(n.start), offset=float(n.end)))
    events.sort(key=lambda e: (e.onset, e.midi))
    return events


def note_to_japanese_solfege(note_name: str) -> str:
    """Convert note label (e.g., C#4) to Japanese solfege-friendly text."""
    letter = note_name[0].upper()
    accidental = ""
    if len(note_name) >= 2 and note_name[1] in {"#", "b"}:
        accidental = "シャープ" if note_name[1] == "#" else "フラット"
    base = SOLFEGE_JP.get(letter, letter)
    return f"{base}{accidental}" if accidental else base


def format_notes_text(events: list[NoteEvent], japanese_solfege: bool = False) -> str:
    """Render events as newline-separated text."""
    lines: list[str] = []
    for ev in events:
        row = f"{ev.name}\t(midi={ev.midi}, start={ev.onset:.3f}, dur={ev.duration:.3f})"
        if japanese_solfege:
            row += f"\t{note_to_japanese_solfege(ev.name)}"
        lines.append(row)
    return "\n".join(lines)


def write_notes_file(events: list[NoteEvent], output_path: Path, japanese_solfege: bool = False) -> Path:
    """Write notes.txt file."""
    output_path.write_text(format_notes_text(events, japanese_solfege=japanese_solfege), encoding="utf-8")
    return output_path
