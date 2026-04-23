"""ASCII TAB parsing utilities for melody-tab output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

TAB_STRING_LABELS = ["e", "B", "G", "D", "A", "E"]
OPEN_STRING_MIDI = [64, 59, 55, 50, 45, 40]


@dataclass(slots=True)
class ParsedTabEvent:
    """One note event detected in ASCII TAB."""

    string_index: int  # 0=high e, 5=low E
    fret: int
    column: int

    @property
    def string_number(self) -> int:
        """Human-facing string number (1=high e .. 6=low E)."""
        return self.string_index + 1

    @property
    def midi(self) -> int:
        """MIDI pitch from standard tuning + fret."""
        return OPEN_STRING_MIDI[self.string_index] + self.fret


def _extract_tab_segments(tab_text: str) -> list[str]:
    segments: dict[str, str] = {}
    for raw_line in tab_text.splitlines():
        line = raw_line.rstrip("\n")
        if not line or line.lstrip().startswith("#"):
            continue

        if "|" not in line:
            continue
        label, rest = line.split("|", 1)
        label = label.strip()
        if label not in TAB_STRING_LABELS or label in segments:
            continue

        right_bar = rest.rfind("|")
        segment = rest if right_bar < 0 else rest[:right_bar]
        segments[label] = segment

    missing = [label for label in TAB_STRING_LABELS if label not in segments]
    if missing:
        raise ValueError(f"TAB parse failed: missing string lines: {', '.join(missing)}")

    widths = {len(segments[label]) for label in TAB_STRING_LABELS}
    if len(widths) != 1:
        raise ValueError("TAB parse failed: string lines are not horizontally aligned")

    return [segments[label] for label in TAB_STRING_LABELS]


def parse_ascii_tab(tab_text: str) -> list[ParsedTabEvent]:
    """Parse six-string ASCII TAB into note events."""
    segments = _extract_tab_segments(tab_text)
    events: list[ParsedTabEvent] = []

    for string_index, segment in enumerate(segments):
        col = 0
        n = len(segment)
        while col < n:
            ch = segment[col]

            if ch.isdigit():
                start = col
                while col < n and segment[col].isdigit():
                    col += 1
                fret = int(segment[start:col])
                events.append(ParsedTabEvent(string_index=string_index, fret=fret, column=start))
                continue

            # '-' means empty/continuation, 'x' means muted/non-playable marker.
            if ch in {"-", "x", "X"}:
                col += 1
                continue

            # ignore other decorative glyphs/spaces
            col += 1

    events.sort(key=lambda ev: (ev.column, ev.string_index))
    return events


def parse_tab_file(path: Path) -> list[ParsedTabEvent]:
    """Parse events from a TAB text file."""
    return parse_ascii_tab(path.read_text(encoding="utf-8"))
