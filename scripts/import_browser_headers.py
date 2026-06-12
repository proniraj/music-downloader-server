#!/usr/bin/env python3
"""
Import YouTube Music browser headers from a file into browser.json.

Mac-friendly alternative to `ytmusicapi browser` (no Ctrl-D needed).

Usage:
  1. DevTools → Network → browse request → copy Request Headers
  2. Paste into headers.txt (must include authorization + cookie)
  3. python scripts/import_browser_headers.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from ytmusicapi import setup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "headers.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "browser.json"


def _ensure_required_headers(raw: str) -> str:
    """Add common missing headers so ytmusicapi setup succeeds."""
    lines = raw.splitlines()
    lower_keys = {line.split(":", 1)[0].strip().lower() for line in lines if ":" in line and not line.startswith(":")}

    if "x-goog-authuser" not in lower_keys:
        lines.append("x-goog-authuser: 0")

    if "x-origin" not in lower_keys:
        lines.append("x-origin: https://music.youtube.com")

    return "\n".join(lines)


def main() -> None:
    headers_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT

    if not headers_file.is_file():
        print(f"Missing {headers_file}")
        print("Paste DevTools request headers into that file, then run again.")
        sys.exit(1)

    raw = headers_file.read_text()
    if "authorization" not in raw.lower() or "cookie" not in raw.lower():
        print("headers.txt must include authorization and cookie lines.")
        sys.exit(1)

    prepared = _ensure_required_headers(raw)
    setup(filepath=str(output_file), headers_raw=prepared)
    print(f"Created {output_file.resolve()}")
    print("Set in .env: YTMUSIC_AUTH=browser and YTMUSIC_BROWSER_FILE=browser.json")


if __name__ == "__main__":
    main()
