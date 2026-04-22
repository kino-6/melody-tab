from melody_tab.models import NoteEvent
from melody_tab.tab import TabConfig, candidate_positions, choose_positions, movement_cost


def _n(midi: int) -> NoteEvent:
    return NoteEvent(midi=midi, name="X", onset=0.0, offset=1.0)


def test_candidate_positions_basic():
    pos = candidate_positions(64, lowest_fret=0, highest_fret=20)  # E4
    assert any(p.string_index == 0 and p.fret == 0 for p in pos)
    assert any(p.string_index == 1 and p.fret == 5 for p in pos)


def test_movement_cost_prefers_smaller_shifts():
    near = movement_cost(None, candidate_positions(64, 0, 12)[0], preferred_fret_max=12)
    far = movement_cost(None, candidate_positions(76, 0, 20)[0], preferred_fret_max=8)
    assert near < far


def test_choose_positions_prefers_more_playable_path():
    events = [_n(64), _n(66), _n(67), _n(69)]
    positions, _, stats = choose_positions(events, config=TabConfig(lowest_fret=0, highest_fret=12, preferred_fret_max=7))
    assert stats.dropped_notes == 0
    assert all(p is not None for p in positions)
    # should stay in low frets and avoid huge jumps for this phrase
    assert max(p.fret for p in positions if p is not None) <= 7


def test_choose_positions_octave_shift_when_out_of_range():
    events = [_n(96)]
    positions, norm, stats = choose_positions(events, config=TabConfig(lowest_fret=0, highest_fret=20, octave_shift_outliers=True))
    assert positions[0] is not None
    assert norm[0].midi == 84
    assert stats.octave_shifted == 1
