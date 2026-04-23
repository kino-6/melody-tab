#!/usr/bin/env bash
set -euo pipefail

uv venv
uv pip install -e .
uv pip install --upgrade "setuptools<82" "basic-pitch[onnx]"
uv pip install -e '.[dev]'

echo "Setup complete."
echo "Run with:"
echo "  chmod +x run.sh"
echo "  ./run.sh --help"
echo "./run.sh "https://www.youtube.com/watch?v=...""
