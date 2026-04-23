from melody_tab.tab_parse import OPEN_STRING_MIDI, parse_ascii_tab
from melody_tab.tab_to_midi import TimedNote, tab_events_to_timed_notes


def test_parse_multidigit_fret_and_alignment():
    tab = "\n".join(
        [
            "e|--12----|",
            "B|--------|",
            "G|--------|",
            "D|--------|",
            "A|--------|",
            "E|--------|",
        ]
    )
    events = parse_ascii_tab(tab)
    assert len(events) == 1
    assert events[0].string_number == 1
    assert events[0].fret == 12
    assert events[0].column == 2


def test_muted_x_is_ignored():
    tab = "\n".join(
        [
            "e|--x-----|",
            "B|--------|",
            "G|--------|",
            "D|--------|",
            "A|--------|",
            "E|--------|",
        ]
    )
    assert parse_ascii_tab(tab) == []


def test_string_to_midi_mapping():
    tab = "\n".join(
        [
            "e|0-------|",
            "B|0-------|",
            "G|0-------|",
            "D|0-------|",
            "A|0-------|",
            "E|0-------|",
        ]
    )
    events = parse_ascii_tab(tab)
    assert [e.midi for e in events] == OPEN_STRING_MIDI


def test_column_alignment_generates_simultaneous_notes():
    tab = "\n".join(
        [
            "e|--0-----|",
            "B|--1-----|",
            "G|--------|",
            "D|--------|",
            "A|--------|",
            "E|--------|",
        ]
    )
    events = parse_ascii_tab(tab)
    timed = tab_events_to_timed_notes(events, tempo=120.0, step_beats=0.5)
    assert len(timed) == 2
    assert timed[0].start == timed[1].start


def test_timing_alignment_from_notes_sequence():
    tab = "\n".join(
        [
            "e|0---2---|",
            "B|--------|",
            "G|--------|",
            "D|--------|",
            "A|--------|",
            "E|--------|",
        ]
    )
    events = parse_ascii_tab(tab)
    timing = [TimedNote(midi=64, start=1.0, duration=0.25), TimedNote(midi=66, start=2.0, duration=0.75)]
    timed = tab_events_to_timed_notes(events, timing_notes=timing)
    assert [n.start for n in timed] == [1.0, 2.0]
    assert [n.duration for n in timed] == [0.25, 0.75]
