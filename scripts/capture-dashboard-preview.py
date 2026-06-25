#!/usr/bin/env python3
"""Render a captured Herdr dashboard ANSI frame to an SVG preview.

Usage:
  herdr pane read <pane-id> --source visible --ansi > /tmp/dashboard.ansi
  scripts/capture-dashboard-preview.py /tmp/dashboard.ansi docs/dashboard-preview.svg
"""

from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")


@dataclass
class Style:
    fg: str = "#e5e7eb"
    bg: str | None = None
    bold: bool = False
    italic: bool = False

    def copy(self) -> "Style":
        return Style(self.fg, self.bg, self.bold, self.italic)

    def key(self) -> tuple[str, str | None, bool, bool]:
        return (self.fg, self.bg, self.bold, self.italic)


def parse_sgr(params: str, style: Style) -> Style:
    codes = [0] if not params else [int(p) if p else 0 for p in params.split(";")]
    out = style.copy()
    i = 0
    while i < len(codes):
        code = codes[i]
        if code == 0:
            out = Style()
        elif code == 1:
            out.bold = True
        elif code == 3:
            out.italic = True
        elif code == 22:
            out.bold = False
        elif code == 23:
            out.italic = False
        elif code == 39:
            out.fg = "#e5e7eb"
        elif code == 49:
            out.bg = None
        elif code in (38, 48) and i + 4 < len(codes) and codes[i + 1] == 2:
            r, g, b = codes[i + 2 : i + 5]
            color = f"#{r:02x}{g:02x}{b:02x}"
            if code == 38:
                out.fg = color
            else:
                out.bg = color
            i += 4
        i += 1
    return out


def parse_ansi(raw: str):
    lines = []
    cur_line = []
    style = Style()
    run_text = []
    run_style = style.copy()

    def flush_run():
        nonlocal run_text
        if run_text:
            cur_line.append(("".join(run_text), run_style.copy()))
            run_text = []

    pos = 0
    for m in ANSI_RE.finditer(raw):
        text = raw[pos : m.start()]
        for ch in text:
            if ch == "\r":
                continue
            if ch == "\n":
                flush_run()
                lines.append(cur_line.copy())
                cur_line.clear()
            else:
                run_text.append(ch)
        flush_run()
        style = parse_sgr(m.group(1), style)
        run_style = style.copy()
        pos = m.end()

    for ch in raw[pos:]:
        if ch == "\r":
            continue
        if ch == "\n":
            flush_run()
            lines.append(cur_line.copy())
            cur_line.clear()
        else:
            run_text.append(ch)
    flush_run()
    if cur_line:
        lines.append(cur_line)
    return lines


def visible_len(runs) -> int:
    return sum(len(text) for text, _ in runs)


def truncate_runs(line, max_cols: int):
    """Clip to terminal width so README preview matches Herdr's visible pane."""
    out = []
    used = 0
    for text, style in line:
        if used >= max_cols:
            break
        remaining = max_cols - used
        clipped = text[:remaining]
        if clipped:
            out.append((clipped, style))
            used += len(clipped)
    return out


def render_svg(lines, max_cols: int = 147) -> str:
    char_w = 9.6
    line_h = 18
    pad_x = 22
    pad_y = 22
    lines = [truncate_runs(line, max_cols) for line in lines]
    width = int(max_cols * char_w + pad_x * 2)
    height = int(len(lines) * line_h + pad_y * 2)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '  <rect width="100%" height="100%" rx="10" fill="#0f172a"/>',
        '  <style>text{font-family:"JetBrains Mono","SFMono-Regular",Menlo,Consolas,monospace;font-size:14px;dominant-baseline:text-before-edge;white-space:pre}</style>',
    ]

    y = pad_y
    for line in lines:
        x_cols = 0
        for text, style in line:
            if not text:
                continue
            x = pad_x + x_cols * char_w
            escaped = html.escape(text)
            attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'fill="{style.fg}"']
            if style.bold:
                attrs.append('font-weight="700"')
            if style.italic:
                attrs.append('font-style="italic"')
            if style.bg:
                # Keep actual header pill backgrounds from Bubble Tea.
                parts.append(
                    f'  <rect x="{x:.1f}" y="{y - 1:.1f}" width="{len(text) * char_w:.1f}" height="{line_h:.1f}" fill="{style.bg}"/>'
                )
            parts.append(f'  <text {" ".join(attrs)}>{escaped}</text>')
            x_cols += len(text)
        y += line_h

    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: capture-dashboard-preview.py INPUT.ansi OUTPUT.svg", file=sys.stderr)
        return 2
    raw = Path(sys.argv[1]).read_text(errors="replace")
    lines = parse_ansi(raw)
    Path(sys.argv[2]).write_text(render_svg(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
