"""Simple monophonic guitar TAB generation."""

from __future__ import annotations

from pathlib import Path

from melody_tab.models import FretPosition, NoteEvent

# string 0 is high E4, 5 is low E2
STANDARD_TUNING_MIDI = [64, 59, 55, 50, 45, 40]
STRING_LABELS = ["e", "B", "G", "D", "A", "E"]


def candidate_positions(midi_note: int, lowest_fret: int = 0, highest_fret: int = 20) -> list[FretPosition]:
    """Return playable positions for midi_note in configured fret window."""
    out: list[FretPosition] = []
    for i, open_pitch in enumerate(STANDARD_TUNING_MIDI):
        fret = midi_note - open_pitch
        if lowest_fret <= fret <= highest_fret:
            out.append(FretPosition(string_index=i, fret=fret))
    return out


def movement_cost(prev: FretPosition | None, curr: FretPosition) -> float:
    """Heuristic cost: mostly fret movement, lightly string changes and high-fret penalty."""
    base = curr.fret * 0.05
    if prev is None:
        return base
    return abs(curr.fret - prev.fret) + abs(curr.string_index - prev.string_index) * 0.35 + base


def choose_positions(
    events: list[NoteEvent], lowest_fret: int = 0, highest_fret: int = 20
) -> list[FretPosition | None]:
    """Greedy monophonic position assignment minimizing local movement cost."""
    chosen: list[FretPosition | None] = []
    prev: FretPosition | None = None
    for ev in events:
        candidates = candidate_positions(ev.midi, lowest_fret=lowest_fret, highest_fret=highest_fret)
        if not candidates:
            chosen.append(None)
            prev = None
            continue
        best = min(candidates, key=lambda c: movement_cost(prev, c))
        chosen.append(best)
        prev = best
    return chosen


def render_ascii_tab(events: list[NoteEvent], positions: list[FretPosition | None]) -> str:
    """Render compact ASCII tab with one column per note event."""
    lines = {label: [] for label in STRING_LABELS}
    markers: list[str] = []

    for ev, pos in zip(events, positions):
        if pos is None:
            for label in STRING_LABELS:
                lines[label].append("-x-")
            markers.append(f"[{ev.name}:OUT]")
            continue

        for i, label in enumerate(STRING_LABELS):
            if i == pos.string_index:
                fret_text = str(pos.fret)
                pad = "-" * max(0, 3 - len(fret_text))
                lines[label].append(f"-{fret_text}{pad}")
            else:
                lines[label].append("---")
        markers.append(ev.name)

    out_rows = [f"# notes: {' '.join(markers)}"]
    for label in STRING_LABELS:
        out_rows.append(f"{label}|" + "".join(lines[label]) + "|")
    return "\n".join(out_rows)


def write_tab_file(events: list[NoteEvent], output_path: Path, lowest_fret: int = 0, highest_fret: int = 20) -> Path:
    """Generate and write tab.txt output."""
    positions = choose_positions(events, lowest_fret=lowest_fret, highest_fret=highest_fret)
    tab_text = render_ascii_tab(events, positions)
    output_path.write_text(tab_text, encoding="utf-8")
    return output_path
