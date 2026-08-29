"""CLI entry: python -m hcx / hcx."""

from __future__ import annotations

import argparse
import logging
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hcx", description="HCX Cursor adapter for Hermes")
    parser.add_argument("--host", default=None, help="Bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Bind port (default 8765)")
    parser.add_argument("--config", default=None, help="Path to hermesxcursor.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from hcx.server import run

    run(host=args.host, port=args.port, config_path=args.config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
