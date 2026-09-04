#!/usr/bin/env python3
"""Construct-Zero help home screen (pyfiglet + Rich)."""

from __future__ import annotations

import os
import sys
import time

SAPPHIRE = "#0F52BA"
SHINE_CORE = "#F5FBFF"
SHINE_EDGE = "#8EC5FF"
BYLINE = "by Anish Sukhramani"

BODY_LINES = (
    "  Talk to Hermes",
    "    ./construct-zero chat",
    '    Opens Hermes in this folder.  (There is no global "hermes" command.)',
    "",
    "  If chat cannot connect",
    "    ./construct-zero start",
    "    Then run ./construct-zero chat again.",
    "",
    "    ./construct-zero start --voice",
    "    Also starts the voice page (the URL is printed).",
    "",
    "  Check that it is working",
    "    ./construct-zero doctor",
    "",
    "  One message, then exit",
    '    ./construct-zero chat -q "hello"',
    "",
    "  Inference on loopback. Cursor pays for the model.",
)

FALLBACK_BANNER = (
    "construct-zero",
)


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip() in ("1", "true", "TRUE", "yes")


def _should_color() -> bool:
    if _env_flag("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    return sys.stdout.isatty()


def _should_animate() -> bool:
    if _env_flag("CZ_HELP_NO_ANIM"):
        return False
    if not _should_color():
        return False
    return sys.stdout.isatty()


def _banner_lines() -> list[str]:
    try:
        from pyfiglet import Figlet
    except ImportError:
        return list(FALLBACK_BANNER)

    cols = 80
    try:
        cols = max(40, min(os.get_terminal_size().columns, 100))
    except OSError:
        pass

    art = ""
    chosen_width = 10_000
    for font in ("slant", "standard", "small"):
        try:
            rendered = Figlet(font=font, width=max(cols, 80)).renderText("construct-zero")
        except Exception:
            continue
        lines = [line.rstrip() for line in rendered.rstrip("\n").splitlines()]
        if not lines:
            continue
        width = max(len(line) for line in lines)
        if width <= cols or font == "small":
            art = "\n".join(lines)
            break
        if width < chosen_width:
            chosen_width = width
            art = "\n".join(lines)
    if not art:
        return list(FALLBACK_BANNER)
    lines = [line.rstrip() for line in art.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return lines or list(FALLBACK_BANNER)


def _plain_help(lines: list[str]) -> str:
    parts = list(lines) + ["", f"  {BYLINE}", ""] + list(BODY_LINES)
    return "\n".join(parts) + "\n"


def _paint_banner(lines: list[str], shine_at: int | None, window: int) -> "object":
    from rich.text import Text

    width = max((len(line) for line in lines), default=0)
    out = Text()
    for i, line in enumerate(lines):
        padded = line.ljust(width)
        for col, ch in enumerate(padded):
            style = SAPPHIRE
            if shine_at is not None and ch != " ":
                dist = col - shine_at
                if 0 <= dist < window:
                    mid = window / 2
                    if abs(dist - mid) <= 1.5:
                        style = f"bold {SHINE_CORE}"
                    else:
                        style = f"bold {SHINE_EDGE}"
            out.append(ch, style=style)
        if i < len(lines) - 1:
            out.append("\n")
    return out


def _body_text() -> "object":
    from rich.text import Text

    out = Text()
    out.append(f"  {BYLINE}\n\n", style=f"italic {SAPPHIRE}")
    for i, line in enumerate(BODY_LINES):
        out.append(line, style=SAPPHIRE)
        if i < len(BODY_LINES) - 1:
            out.append("\n")
    return out


def _screen(lines: list[str], shine_at: int | None, window: int) -> "object":
    from rich.console import Group
    from rich.text import Text

    return Group(
        _paint_banner(lines, shine_at, window),
        Text(""),
        _body_text(),
    )


def _print_rich(lines: list[str]) -> None:
    from rich.console import Console
    from rich.live import Live

    console = Console(highlight=False, color_system="truecolor" if _should_color() else None)
    width = max((len(line) for line in lines), default=0)
    window = 10

    if not _should_animate() or width == 0:
        console.print(_screen(lines, None, window))
        return

    step = 4
    delay = 0.022
    start = -window
    stop = width + 2
    with Live(
        _screen(lines, start, window),
        console=console,
        refresh_per_second=30,
        transient=False,
    ) as live:
        for _pass in range(2):
            col = start
            while col <= stop:
                live.update(_screen(lines, col, window))
                time.sleep(delay)
                col += step
        live.update(_screen(lines, None, window))


def main() -> int:
    lines = _banner_lines()
    try:
        import rich  # noqa: F401

        _print_rich(lines)
    except ImportError:
        sys.stdout.write(_plain_help(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
