from melody_tab.cli import build_parser


def test_cli_parser_smoke():
    parser = build_parser()
    args = parser.parse_args([
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "--start",
        "3",
        "--end",
        "10",
        "--out-dir",
        "output",
        "--japanese-solfege",
        "--lowest-fret",
        "1",
        "--highest-fret",
        "15",
        "--melody-mode",
        "balanced",
        "--min-note-ms",
        "100",
        "--preferred-fret-max",
        "11",
        "--max-jump-semitones",
        "10",
        "--octave-shift-outliers",
        "--debug-melody",
    ])
    assert args.youtube_url.startswith("https://youtube.com")
    assert args.start == 3
    assert args.end == 10
    assert args.japanese_solfege is True
    assert args.lowest_fret == 1
    assert args.highest_fret == 15
    assert args.melody_mode == "balanced"
    assert args.debug_melody is True
    assert args.write_melody_midi is True
    assert args.write_tab_preview_midi is True
    assert args.write_compare_report is True
