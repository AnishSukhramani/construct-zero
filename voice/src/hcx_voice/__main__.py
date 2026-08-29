"""CLI: python -m hcx_voice"""

from __future__ import annotations

import argparse
import logging
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hcx-voice", description="HCX hold-to-talk voice sidecar")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from hcx_voice.server import run

    run(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
