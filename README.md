# melody-tab
Extract melody from audio (YouTube, humming, whistle) and convert it to MIDI, note names, and simple guitar TAB.

# melody-tab

Extract melody from audio (YouTube, humming, whistle) and convert it to MIDI, note names, and simple guitar TAB.

---

## ✨ Overview

`melody-tab` is a local-first CLI tool for melody extraction.

It converts audio into structured musical data using an audio-to-MIDI pipeline.


YouTube / audio
↓
audio extraction
↓
MIDI transcription
↓
note parsing
↓
TAB generation


---

## 🎯 Use Cases

- Transcribe humming or whistling into notes
- Extract melody from YouTube clips
- Quickly get note sequences without manual piano input
- Generate rough guitar TAB from melody

---

## 🧠 Key Concept

This tool is based on:

- **Automatic Music Transcription (AMT)**  
  Converting audio signals into symbolic music (MIDI / notes)

- **Pitch Detection**  
  Estimating fundamental frequency from audio

---

## ⚠️ Limitations

- Designed for **monophonic (single-note) melody**
- Polyphonic audio (e.g. full piano songs) may produce noisy results
- Output may require manual cleanup in MuseScore or similar tools
- TAB generation is heuristic-based, not optimal fingering

---

## 🚀 Features (MVP)

- YouTube audio extraction
- WAV conversion
- MIDI transcription
- Note name extraction (C4, D#4)
- Optional Japanese solfege (ドレミ)
- Simple guitar TAB generation

---

## 🔧 Requirements

- Python 3.11
- ffmpeg (required for audio processing)

---

## 📦 Installation

### Using pip
```bash
pip install -r requirements.txt
```

Using uv (recommended)
uv sync
▶️ Usage

melody-tab "https://youtube.com/..." --start 30 --end 45

Output:
output.mid
notes.txt
tab.txt
🛠 Architecture
download.py — audio extraction (yt-dlp)
audio.py — preprocessing / trimming
transcribe.py — audio → MIDI
notes.py — MIDI → note names
tab.py — note → guitar TAB
📌 Future Improvements
Better polyphonic handling
Rhythm quantization
Multiple instrument support
GUI / Web UI
Guitar fingering optimization
⚖️ Legal

Use only audio you have the right to process locally.
