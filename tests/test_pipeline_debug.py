from pathlib import Path

from melody_tab.melody import MelodyConfig, extract_melody
from melody_tab.models import NoteEvent
from melody_tab.notes import format_notes_text, midi_to_note_events, write_note_events_midi
from melody_tab.tab import TabConfig, write_tab_file
from melody_tab.tab_to_midi import (
    compare_melody_to_tab,
    format_comparison,
    load_notes_timing,
    tab_to_midi_pipeline,
)


def _ev(midi: int, onset: float, offset: float, name: str = "X") -> NoteEvent:
    return NoteEvent(midi=midi, name=name, onset=onset, offset=offset)


def test_write_melody_midi_contains_melody_notes_only(tmp_path: Path):
    melody_events = [_ev(64, 0.0, 0.3), _ev(67, 0.3, 0.6), _ev(69, 0.6, 0.9)]
    out = tmp_path / "melody.mid"
    write_note_events_midi(melody_events, out)

    parsed = midi_to_note_events(out)
    assert [n.midi for n in parsed] == [64, 67, 69]


def test_tab_is_generated_from_supplied_melody_notes(tmp_path: Path):
    raw_events = [_ev(52, 0.0, 0.2, "E3"), _ev(64, 0.0, 0.2, "E4"), _ev(67, 0.2, 0.4, "G4")]
    melody_events = [_ev(64, 0.0, 0.2, "E4"), _ev(67, 0.2, 0.4, "G4")]
    tab_path = tmp_path / "tab.txt"
    write_tab_file(melody_events, tab_path, config=TabConfig())

    text = tab_path.read_text(encoding="utf-8")
    assert "# notes: E4 G4" in text
    assert "E3" not in text
    assert len(raw_events) > len(melody_events)


def test_tab_preview_midi_is_produced_from_tab(tmp_path: Path):
    tab_text = "\n".join(
        [
            "e|0---2---|",
            "B|--------|",
            "G|--------|",
            "D|--------|",
            "A|--------|",
            "E|--------|",
        ]
    )
    tab_path = tmp_path / "tab.txt"
    tab_path.write_text(tab_text, encoding="utf-8")

    notes_path = tmp_path / "notes_melody.txt"
    notes_path.write_text(
        format_notes_text([_ev(64, 0.0, 0.25), _ev(66, 0.5, 0.75)]),
        encoding="utf-8",
    )

    out = tab_to_midi_pipeline(
        tab_path=tab_path,
        out_path=tmp_path / "tab_preview.mid",
        timing_from_notes=notes_path,
        compare_with_notes=notes_path,
    )

    assert out.midi_path.exists()
    assert out.comparison_path is not None
    assert out.comparison_path.exists()


def test_compare_report_detects_simple_mismatch(tmp_path: Path):
    melody_notes_path = tmp_path / "notes_melody.txt"
    melody_notes_path.write_text(
        "\n".join(
            [
                "C4\t(midi=60, start=0.000, dur=0.500)",
                "D4\t(midi=62, start=0.500, dur=0.500)",
            ]
        ),
        encoding="utf-8",
    )
    melody_notes = load_notes_timing(melody_notes_path)
    tab_notes = [
        type(melody_notes[0])(midi=60, start=0.0, duration=0.5),
        type(melody_notes[0])(midi=74, start=0.5, duration=0.5),
    ]

    result = compare_melody_to_tab(tab_notes, melody_notes)
    report = format_comparison(result)
    assert "pitch-mismatches: 1" in report
    assert "extra-notes: 1" in report
    assert "missing-notes: 1" in report


def test_raw_to_melody_note_count_shrinks_in_controlled_fixture():
    raw_events = [
        _ev(60, 0.0, 0.03),  # short, should drop
        _ev(64, 0.05, 0.30),
        _ev(67, 0.05, 0.30),
        _ev(64, 0.31, 0.60),
    ]

    melody, stats, *_ = extract_melody(raw_events, MelodyConfig(mode="highest", min_note_ms=50))
    assert len(melody) < len(raw_events)
    assert stats.raw_notes == len(raw_events)
    assert stats.dropped_short == 1
