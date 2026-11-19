#!/usr/bin/env python3
"""Draw README SVG labels as outlines, using the site's fonts and palette."""

from __future__ import annotations

from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

# Site palette (westonrosch.com)
BG = "#05080f"
BG2 = "#0a1220"
SURFACE = "#0f1a2b"
SLATE = "#4b5d73"
LINE = "#a0b9d7"
SKY = "#5cc8f5"
SAGE = "#8fd1ae"
TEXT = "#c9d3de"
WHITE = "#f2f5f8"
TEXT2 = "#91a0ae"
TEXT3 = "#6e7c89"

FONTS = Path(__file__).resolve().parent.parent / "fonts"
SERIF = FONTS / "InstrumentSerif-Regular.ttf"
SERIF_ITALIC = FONTS / "InstrumentSerif-Italic.ttf"
MONO_MED = FONTS / "IBMPlexMono-Medium.ttf"
MONO_REG = FONTS / "IBMPlexMono-Regular.ttf"

_hb_faces: dict[str, hb.Face] = {}
_tt_fonts: dict[str, TTFont] = {}

import re

def _compact_path(d: str) -> str:
    if not d:
        return d
    def repl(m: re.Match) -> str:
        n = float(m.group())
        return f"{n:.2f}".rstrip("0").rstrip(".")
    return re.sub(r"-?\d+\.\d+", repl, d)




def _face(path: str | Path) -> hb.Face:
    path = str(path)
    if path not in _hb_faces:
        _hb_faces[path] = hb.Face(Path(path).read_bytes())
    return _hb_faces[path]


def _tt(path: str | Path) -> TTFont:
    path = str(path)
    if path not in _tt_fonts:
        _tt_fonts[path] = TTFont(path)
    return _tt_fonts[path]


def measure(font_path, text: str, size: float, letter_spacing: float = 0) -> float:
    if not text:
        return 0.0
    face = _face(font_path)
    font = hb.Font(face)
    upem = face.upem
    font.scale = (upem, upem)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf)
    scale = size / upem
    adv = sum(p.x_advance for p in buf.glyph_positions) * scale
    if len(buf.glyph_infos) > 1:
        adv += letter_spacing * (len(buf.glyph_infos) - 1)
    return adv


def text_paths(
    font_path,
    text: str,
    size: float,
    x: float,
    y: float,
    fill: str,
    letter_spacing: float = 0,
) -> tuple[str, float]:
    """Return SVG path markup and advance width. y is the baseline, SVG y-down."""
    if not text:
        return "", 0.0
    tt = _tt(font_path)
    glyphset = tt.getGlyphSet()
    glyph_order = tt.getGlyphOrder()
    face = _face(font_path)
    hb_font = hb.Font(face)
    upem = face.upem
    hb_font.scale = (upem, upem)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf)
    scale = size / upem
    parts = []
    pen_x, pen_y = x, y
    infos, positions = buf.glyph_infos, buf.glyph_positions
    for i, (info, pos) in enumerate(zip(infos, positions)):
        name = glyph_order[info.codepoint]
        dx = pos.x_offset * scale
        dy = pos.y_offset * scale
        spen = SVGPathPen(glyphset)
        tpen = TransformPen(spen, (scale, 0, 0, -scale, pen_x + dx, pen_y - dy))
        glyphset[name].draw(tpen)
        d = _compact_path(spen.getCommands())
        if d:
            parts.append(f'<path d="{d}" fill="{fill}"/>')
        extra = letter_spacing if i < len(infos) - 1 else 0
        pen_x += pos.x_advance * scale + extra
        pen_y -= pos.y_advance * scale
    return "\n".join(parts), pen_x - x


def text_paths_right(font_path, text, size, right, y, fill, letter_spacing=0):
    w = measure(font_path, text, size, letter_spacing)
    return text_paths(font_path, text, size, right - w, y, fill, letter_spacing)


def ellipsize(font_path, text: str, size: float, max_width: float, letter_spacing: float = 0) -> str:
    if measure(font_path, text, size, letter_spacing) <= max_width:
        return text
    ell = "…"
    for i in range(len(text), 0, -1):
        candidate = text[:i].rstrip() + ell
        if measure(font_path, candidate, size, letter_spacing) <= max_width:
            return candidate
    return ell


def escape_attr(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;")


def save_svg(path: Path, width: int, height: int, body: str, title: str) -> None:
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape_attr(title)}">
{body}
</svg>
'''
    path.write_text(svg)
    print(f"wrote {path} ({path.stat().st_size/1024:.1f} KB)")


# Shared CSS: color-scheme edge contrast + reduced-motion hide
PANEL_CSS = """
<style>
  @media (prefers-color-scheme: light) {
    .panel-bg { stroke: #a0b9d7; stroke-opacity: .42; stroke-width: 1; }
  }
  @media (prefers-reduced-motion: reduce) {
    .motion { display: none !important; }
  }
</style>
"""
