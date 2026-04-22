# melody-tab

Local-first Python CLI to extract a **melody-focused** transcription from a YouTube URL and export:

- MIDI (`.mid`) for MuseScore cleanup
- note list (`notes.txt`) with optional Japanese solfege (ドレミ)
- simple monophonic guitar TAB (`tab.txt`)

> Intended for lawful personal analysis workflows only. Only process audio you have rights to use.

## MVP scope and limitations

This project is intentionally practical and melody-oriented:

- Works best on humming, whistling, sung melody, and melody-dominant passages.
- Not designed to perfectly transcribe dense polyphonic piano/chords.
- Rhythm/timing can require manual cleanup after MIDI import into MuseScore.
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
  tab.py
  models.py
  utils.py
tests/
  test_notes.py
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
  --lowest-fret 0 \
  --highest-fret 15
```

### CLI options

- positional `youtube_url`
- `--start <seconds>` optional trim start
- `--end <seconds>` optional trim end (must be greater than start)
- `--out-dir <path>` output directory (default: `output`)
- `--keep-intermediate` keep downloaded/intermediate audio files
- `--japanese-solfege` include ドレミ text in `notes.txt`
- `--lowest-fret <int>` minimum fret for TAB assignment (default `0`)
- `--highest-fret <int>` maximum fret for TAB assignment (default `20`)

## Output files

In `--out-dir`:

- `melody.mid`
- `notes.txt`
- `tab.txt`

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
  - Some online examples use the Python API (`predict_and_save`) in ways that no longer match newer releases.
  - For MVP stability, this project uses the `basic-pitch` CLI instead of direct Python API calls.
  - Verify CLI availability in your active venv: `basic-pitch --help`
  - Reinstall dependencies in a clean Python 3.11 venv if CLI invocation fails.
- **No notes detected**
  - Use melody-dominant sections.
  - Trim to a smaller range with clearer lead melody.
- **TAB has `OUT` notes**
  - Expand fret range using `--lowest-fret` / `--highest-fret`.

## Future improvements

- Backend choice (`basic-pitch` / alternative melody estimators)
- Better onset filtering and de-duplication for cleaner monophonic notes
- Optional quantization and beat grid assistance
- Better global optimization for guitar fingering
- Optional direct local audio-file input mode
