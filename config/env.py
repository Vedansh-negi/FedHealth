"""Tiny .env loader (no extra dependency). Real environment variables win."""

import os
from pathlib import Path

_LOADED = False


def load_env():
    global _LOADED
    if _LOADED:
        return
    _LOADED = True

    root = Path(__file__).resolve().parent.parent
    for candidate in (root / ".env", root / "backend" / ".env"):
        if not candidate.is_file():
            continue
        for raw_line in candidate.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))
