"""Compatibility launcher for the refactored RCS package."""

from __future__ import annotations

import sys
import traceback

from rcs.main import main


def _run() -> None:
    """Run the GUI, keeping the console open on errors."""

    try:
        main()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        if sys.stdin.isatty():
            input("\nPress Enter to exit...")
        raise SystemExit(1)


if __name__ == "__main__":
    _run()
