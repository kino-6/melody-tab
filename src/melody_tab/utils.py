"""Utility helpers for process execution and logging."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path


def setup_logging(verbose: bool = True) -> None:
    """Set package logging configuration."""
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def run_command(cmd: list[str], *, cwd: Path | None = None, context: str = "command") -> None:
    """Run subprocess command and raise RuntimeError with actionable stderr on failure."""
    try:
        subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required executable not found while running {context}: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        details = stderr or stdout or "No error output captured"
        raise RuntimeError(f"Failed to run {context}: {details}") from exc
