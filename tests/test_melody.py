from melody_tab.melody import MelodyConfig, extract_melody
from melody_tab.models import NoteEvent


def _ev(midi: int, onset: float, offset: float) -> NoteEvent:
    return NoteEvent(midi=midi, name="X", onset=onset, offset=offset)


def test_overlap_reduced_to_single_melody_note():
    events = [
        _ev(60, 0.0, 0.5),
        _ev(67, 0.0, 0.6),
        _ev(64, 0.0, 0.6),
    ]
    melody, stats, *_ = extract_melody(events, MelodyConfig(mode="highest", min_note_ms=10))
    assert len(melody) >= 1
    assert melody[0].midi == 67
    assert stats.raw_notes == 3


def test_short_notes_removed():
    events = [_ev(64, 0.0, 0.02), _ev(65, 0.1, 0.4)]
    melody, stats, *_ = extract_melody(events, MelodyConfig(min_note_ms=50))
    assert stats.dropped_short == 1
    assert all(n.midi == 65 for n in melody)


def test_out_of_range_shift_or_skip():
    events = [_ev(100, 0.0, 0.3), _ev(20, 0.4, 0.8)]
    melody_shift, stats_shift, *_ = extract_melody(events, MelodyConfig(octave_shift_outliers=True, min_note_ms=10))
    assert len(melody_shift) >= 1
    assert stats_shift.octave_shifted >= 1

    melody_no_shift, stats_no_shift, *_ = extract_melody(events, MelodyConfig(octave_shift_outliers=False, min_note_ms=10))
    assert len(melody_no_shift) == 0
    assert stats_no_shift.dropped_unplayable == 2
