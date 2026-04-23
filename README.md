# melody-tab

Local-first Python CLI to extract a **melody-focused** transcription from a YouTube URL and export:

- MIDI (`.mid`) for MuseScore cleanup
- raw parsed notes (`notes_raw.txt`)
- extracted monophonic melody notes (`notes_melody.txt`, plus compatibility `notes.txt`)
- optimized monophonic guitar TAB (`tab.txt`)
- optional melody scoring diagnostics (`melody_debug.txt`)

> Intended for lawful personal analysis workflows only. Only process audio you have rights to use.

## Why this post-processing stage exists

Raw audio-to-MIDI transcription often contains:

- accompaniment notes mixed with lead notes,
- short noisy note fragments,
- large octave jumps,
- notes outside practical guitar range.

The previous MVP mapped these raw notes directly to TAB note-by-note. That created many `x` placeholders and awkward jumps. The updated pipeline adds a dedicated melody extraction stage and a global TAB path optimizer to improve playability while keeping the architecture simple and local.

## MVP scope and limitations

This project is intentionally practical and melody-oriented:

- Works best on humming, whistling, sung melody, and melody-dominant passages.
- Not designed to perfectly transcribe dense polyphonic piano/chords.
- Rhythm/timing can still require manual cleanup after MIDI import into MuseScore.
- TAB output is heuristic ASCII TAB for monophonic melody, not Guitar Pro-grade fingering.

## Tech stack

- Python 3.11
- `yt-dlp` for local audio download
- `ffmpeg` for conversion/trimming
- Spotify `basic-pitch` for audio-to-MIDI
- `pretty-midi` for MIDI note parsing

## Repository layout

```text
pyproject.toml
src/melody_tab/
  __init__.py
  __main__.py
  cli.py
  download.py
  audio.py
  transcribe.py
  notes.py
  melody.py
  tab.py
  models.py
  utils.py
tests/
  test_notes.py
  test_melody.py
  test_tab.py
  test_cli_smoke.py
README.md
```

## Prerequisites

Install `ffmpeg` first.

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y ffmpeg`

## Install

### Option A: uv (recommended)

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
uv pip install --upgrade "setuptools<82" "basic-pitch[onnx]"
uv pip install -e '.[dev]'
```

### Option B: pip

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
pip install -e .[dev]
```

## Usage

### Module entrypoint

```bash
python -m melody_tab "https://youtube.com/watch?v=..."
```

### Script entrypoint

```bash
melody-tab "https://youtube.com/watch?v=..." \
  --start 30 \
  --end 45 \
  --out-dir output \
  --japanese-solfege \
  --melody-mode balanced \
  --min-note-ms 90 \
  --max-jump-semitones 12 \
  --lowest-fret 0 \
  --preferred-fret-max 12 \
  --highest-fret 15 \
  --octave-shift-outliers \
  --debug-melody
```

## Pipeline

1. Parse MIDI note events.
2. Clean notes (drop short noise, merge repeats, range handling).
3. Extract monophonic melody by scoring candidates per time slice.
4. Generate candidate guitar positions for each melody note.
5. Select full-phrase fingering path using dynamic programming.
6. Render TAB and note/debug outputs.

## Melody extraction heuristics

Candidate scoring combines:

- duration reward,
- pitch-range reward,
- mode preference (`highest`, `duration`, `balanced`),
- continuity penalty for large pitch jumps.

Pre-cleaning includes:

- `--min-note-ms` filtering,
- optional merging of repeated near-identical adjacent notes,
- optional octave shifting into melody range,
- dropping unplayable outliers.

## TAB optimization heuristics

For each melody note, all candidate (string, fret) positions in configured fret bounds are generated. A dynamic-programming pass minimizes global transition cost, preferring:

- lower frets,
- limited hand movement,
- smaller string skips,
- staying near local position windows,
- avoiding frets above `--preferred-fret-max` unless needed.

When a note has no playable position:

- octave shift is attempted (if enabled), otherwise
- a clear `x` marker is emitted.

## CLI options

Core:

- positional `youtube_url`
- `--start <seconds>` optional trim start
- `--end <seconds>` optional trim end (must be greater than start)
- `--out-dir <path>` output directory (default: `output`)
- `--keep-intermediate` keep downloaded/intermediate audio files
- `--japanese-solfege` include ドレミ text in note files

Melody controls:

- `--melody-mode highest|duration|balanced` (default `balanced`)
- `--min-note-ms <float>` (default `90`)
- `--max-jump-semitones <int>` (default `12`)
- `--octave-shift-outliers` enable octave-shift fallback
- `--debug-melody` write `melody_debug.txt`

TAB controls:

- `--lowest-fret <int>` minimum fret (default `0`)
- `--preferred-fret-max <int>` preferred upper fret before penalties (default `12`)
- `--highest-fret <int>` hard maximum fret (default `20`)

## Output files

In `--out-dir`:

- `melody.mid`
- `notes_raw.txt`
- `notes_melody.txt`
- `notes.txt` (compatibility copy of melody notes)
- `tab.txt` (from melody notes only)
- `melody_debug.txt` (if `--debug-melody`)

`tab.txt` includes metadata header lines such as source URL, fret range, dropped-note count, and octave-shift count.


## TAB-to-MIDI verification pipeline

This repository now includes a reverse conversion step for verification:

`ASCII TAB -> MIDI preview`

Why it helps:

- lets you listen to generated TAB and quickly catch wrong pitches,
- creates a practical feedback loop for TAB quality,
- supports future regression checks by comparing TAB-derived notes to `notes_melody.txt`.

### Quick command

```bash
melody-tab --tab-to-midi output/tab.txt --out output/preview.mid
```

Optional timing and comparison helpers:

```bash
melody-tab --tab-to-midi output/tab.txt \
  --out output/preview.mid \
  --tempo 120 \
  --step-beats 0.5 \
  --timing-from-notes output/notes_melody.txt \
  --compare-with-notes output/notes_melody.txt
```

This writes:

- `preview.mid` (TAB-derived MIDI preview)
- `tab_parsed_notes.txt` (string, fret, midi, pitch, tab-column debug table)
- `tab_melody_comparison.txt` (if comparison mode enabled)

### Rhythm reconstruction limitations

ASCII TAB primarily stores horizontal ordering, not exact note lengths. The TAB-to-MIDI exporter therefore uses:

- constant step timing by default (`--tempo`, `--step-beats`), or
- timing borrowed from `notes_melody.txt` when available (`--timing-from-notes`).

This mode is meant for practical pitch verification, not perfect rhythmic score recovery.

### Recommended verification workflow

1. Generate melody notes (`notes_melody.txt`).
2. Generate TAB (`tab.txt`).
3. Convert TAB back to MIDI preview (`--tab-to-midi`).
4. Listen and compare with intended melody.
5. Inspect `tab_parsed_notes.txt` / comparison report for mismatches.

## Recommended workflow

For melody-heavy material:

1. Clip a short melody-dominant section with `--start/--end`.
2. Start with defaults + `--octave-shift-outliers`.
3. If noisy, raise `--min-note-ms` (e.g., 120–160).
4. If contour is too jumpy, lower `--max-jump-semitones`.
5. Inspect `melody_debug.txt` and adjust mode/thresholds.
6. Perform final polish in MuseScore if needed.

## Test

```bash
pytest
```

## Troubleshooting

- **`yt-dlp` failure / URL errors**
  - Ensure URL is valid and accessible from your network.
  - Retry with a shorter clip via `--start/--end`.
- **`ffmpeg` not found**
  - Install ffmpeg and ensure it is in PATH.
- **`basic-pitch` API mismatch / transcription errors**
  - For MVP stability, this project uses the `basic-pitch` CLI instead of direct Python API calls.
  - Verify CLI availability in your active venv: `basic-pitch --help`
  - Reinstall dependencies in a clean Python 3.11 venv if CLI invocation fails.
- **No notes detected / no melody left**
  - Use melody-dominant sections.
  - Lower `--min-note-ms` if extraction is too strict.

## Known limitations

- Heuristic extraction can still choose wrong notes in dense mixes.
- Durations in `notes_melody.txt` are slice-based approximations.
- TAB cost model is practical, not a full physical hand model.
- Rhythmic notation is not quantized for score-perfect output.
