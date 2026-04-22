from melody_tab.notes import note_to_japanese_solfege


def test_solfege_plain_notes():
    assert note_to_japanese_solfege("C4") == "ド"
    assert note_to_japanese_solfege("A3") == "ラ"


def test_solfege_accidental_notes():
    assert note_to_japanese_solfege("F#4") == "ファシャープ"
    assert note_to_japanese_solfege("Bb2") == "シフラット"
