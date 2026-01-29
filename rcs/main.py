"""Entry point for launching the Radar RCS GUI."""

from __future__ import annotations


def main() -> None:
    from .gui import run_app

    run_app()


if __name__ == "__main__":
    main()
