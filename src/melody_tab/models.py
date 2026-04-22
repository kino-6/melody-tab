"""Core data models used across modules."""

from dataclasses import dataclass


@dataclass(slots=True)
class NoteEvent:
    """Represents one monophonic note event parsed from MIDI."""

    midi: int
    name: str
    onset: float
    offset: float

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return max(0.0, self.offset - self.onset)


@dataclass(slots=True)
class FretPosition:
    """One possible fretboard location for a midi pitch."""

    string_index: int  # 0=high E, 5=low E
    fret: int

