from melody_tab.models import FretPosition, NoteEvent
from melody_tab.tab import candidate_positions, choose_positions, movement_cost


def _n(midi: int) -> NoteEvent:
    return NoteEvent(midi=midi, name="X", onset=0.0, offset=1.0)


def test_candidate_positions_basic():
    pos = candidate_positions(64, lowest_fret=0, highest_fret=20)  # E4
    assert any(p.string_index == 0 and p.fret == 0 for p in pos)
    assert any(p.string_index == 1 and p.fret == 5 for p in pos)


def test_movement_cost_prefers_smaller_shifts():
    prev = FretPosition(string_index=1, fret=5)
    near = FretPosition(string_index=1, fret=6)
    far = FretPosition(string_index=4, fret=12)
    assert movement_cost(prev, near) < movement_cost(prev, far)


def test_choose_positions_greedy_continuity():
    events = [_n(64), _n(66), _n(67)]
    chosen = choose_positions(events, lowest_fret=0, highest_fret=12)
    assert all(c is not None for c in chosen)
    assert chosen[0].string_index == 0
