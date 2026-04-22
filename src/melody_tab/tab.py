"""Monophonic guitar TAB generation with global path optimization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from melody_tab.melody import clamp_to_range_with_octave
from melody_tab.models import FretPosition, NoteEvent

# string 0 is high E4, 5 is low E2
STANDARD_TUNING_MIDI = [64, 59, 55, 50, 45, 40]
STRING_LABELS = ["e", "B", "G", "D", "A", "E"]
GUITAR_MIN = 40
GUITAR_MAX = 88


@dataclass(slots=True)
class TabConfig:
    lowest_fret: int = 0
    highest_fret: int = 20
    preferred_fret_max: int = 12
    octave_shift_outliers: bool = True


@dataclass(slots=True)
class TabStats:
    dropped_notes: int = 0
    octave_shifted: int = 0


def candidate_positions(midi_note: int, lowest_fret: int = 0, highest_fret: int = 20) -> list[FretPosition]:
    """Return playable positions for midi_note in configured fret window."""
    out: list[FretPosition] = []
    for i, open_pitch in enumerate(STANDARD_TUNING_MIDI):
        fret = midi_note - open_pitch
        if lowest_fret <= fret <= highest_fret:
            out.append(FretPosition(string_index=i, fret=fret))
    return out


def movement_cost(prev: FretPosition | None, curr: FretPosition, preferred_fret_max: int = 12) -> float:
    """Transition cost balancing hand movement and awkward choices."""
    low_fret_bias = curr.fret * 0.08
    high_fret_penalty = max(0, curr.fret - preferred_fret_max) * 0.75
    if prev is None:
        return low_fret_bias + high_fret_penalty

    fret_jump = abs(curr.fret - prev.fret)
    string_jump = abs(curr.string_index - prev.string_index)
    stretch_penalty = max(0, fret_jump - 4) * 0.5
    string_skip_penalty = max(0, string_jump - 1) * 0.45
    position_window_penalty = max(0, abs(curr.fret - prev.fret) - 7) * 0.7

    return (
        fret_jump * 0.9
        + string_jump * 0.4
        + stretch_penalty
        + string_skip_penalty
        + position_window_penalty
        + low_fret_bias
        + high_fret_penalty
    )


def _prepare_note_for_guitar(midi: int, config: TabConfig) -> tuple[int | None, bool]:
    if config.octave_shift_outliers:
        return clamp_to_range_with_octave(midi, GUITAR_MIN, GUITAR_MAX)
    if GUITAR_MIN <= midi <= GUITAR_MAX:
        return midi, False
    return None, False


def choose_positions(events: list[NoteEvent], config: TabConfig) -> tuple[list[FretPosition | None], list[NoteEvent], TabStats]:
    """Dynamic-programming position assignment across the full phrase."""
    stats = TabStats()
    normalized_events: list[NoteEvent] = []
    candidates_per_note: list[list[FretPosition]] = []

    for ev in events:
        normalized_midi, shifted = _prepare_note_for_guitar(ev.midi, config)
        if normalized_midi is None:
            normalized_events.append(ev)
            candidates_per_note.append([])
            stats.dropped_notes += 1
            continue
        if shifted:
            stats.octave_shifted += 1
        normalized = NoteEvent(midi=normalized_midi, name=ev.name, onset=ev.onset, offset=ev.offset)
        normalized_events.append(normalized)
        candidates_per_note.append(
            candidate_positions(normalized_midi, lowest_fret=config.lowest_fret, highest_fret=config.highest_fret)
        )

    n = len(events)
    if n == 0:
        return [], normalized_events, stats

    dp: list[list[float]] = [[float("inf")] * len(cands) for cands in candidates_per_note]
    back: list[list[int]] = [[-1] * len(cands) for cands in candidates_per_note]

    for i in range(n):
        cands = candidates_per_note[i]
        if not cands:
            continue
        if i == 0:
            for j, c in enumerate(cands):
                dp[i][j] = movement_cost(None, c, preferred_fret_max=config.preferred_fret_max)
            continue

        prev_cands = candidates_per_note[i - 1]
        if not prev_cands:
            for j, c in enumerate(cands):
                dp[i][j] = movement_cost(None, c, preferred_fret_max=config.preferred_fret_max)
            continue

        for j, curr in enumerate(cands):
            best_cost = float("inf")
            best_idx = -1
            for k, prev in enumerate(prev_cands):
                if dp[i - 1][k] == float("inf"):
                    continue
                cost = dp[i - 1][k] + movement_cost(prev, curr, preferred_fret_max=config.preferred_fret_max)
                if cost < best_cost:
                    best_cost = cost
                    best_idx = k
            dp[i][j] = best_cost
            back[i][j] = best_idx

    chosen: list[FretPosition | None] = [None] * n
    last_i = -1
    last_j = -1
    best_terminal = float("inf")
    for i in range(n - 1, -1, -1):
        if not dp[i]:
            continue
        for j, cost in enumerate(dp[i]):
            if cost < best_terminal:
                best_terminal = cost
                last_i, last_j = i, j
        if last_i != -1:
            break

    if last_i != -1:
        i, j = last_i, last_j
        while i >= 0 and j >= 0:
            chosen[i] = candidates_per_note[i][j]
            j = back[i][j]
            i -= 1

    return chosen, normalized_events, stats


def render_ascii_tab(
    events: list[NoteEvent],
    positions: list[FretPosition | None],
    source: str | None = None,
    config: TabConfig | None = None,
    dropped_notes: int = 0,
    octave_shifted: int = 0,
) -> str:
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

    out_rows: list[str] = []
    if source or config:
        out_rows.append("# melody-tab")
        if source:
            out_rows.append(f"# source: {source}")
        if config:
            out_rows.append(f"# fret-range: {config.lowest_fret}-{config.highest_fret} (preferred <= {config.preferred_fret_max})")
        out_rows.append(f"# dropped-notes: {dropped_notes}")
        out_rows.append(f"# octave-shifted: {octave_shifted}")

    out_rows.append(f"# notes: {' '.join(markers)}")
    for label in STRING_LABELS:
        out_rows.append(f"{label}|" + "".join(lines[label]) + "|")
    return "\n".join(out_rows)


def write_tab_file(events: list[NoteEvent], output_path: Path, config: TabConfig, source: str | None = None) -> tuple[Path, TabStats]:
    """Generate and write tab.txt output from melody notes."""
    positions, normalized_events, stats = choose_positions(events, config=config)
    tab_text = render_ascii_tab(
        normalized_events,
        positions,
        source=source,
        config=config,
        dropped_notes=stats.dropped_notes,
        octave_shifted=stats.octave_shifted,
    )
    output_path.write_text(tab_text, encoding="utf-8")
    return output_path, stats
