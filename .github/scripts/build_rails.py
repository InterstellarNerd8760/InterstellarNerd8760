#!/usr/bin/env python3
"""SVG title rails that frame each project screenshot."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgtype import (
    BG,
    LINE,
    MONO_MED,
    PANEL_CSS,
    SERIF,
    SKY,
    WHITE,
    save_svg,
    text_paths,
    text_paths_right,
)

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
W, H = 1400, 56

RAILS = [
    ("rail-lunar.svg", "Lunar Atlas", "NASA Space Apps 2026", "Lunar Atlas, NASA Space Apps 2026"),
    ("rail-centauri.svg", "Centauri Academy", "Live", "Centauri Academy, live"),
    ("rail-x-atlas.svg", "X Network Atlas", "Experiment", "X Network Atlas, experiment"),
    ("rail-walle.svg", "WALL-E1", "In development", "WALL-E1, in development"),
]


def build_rail(filename: str, title: str, meta: str, alt: str) -> None:
    title_paths, tw = text_paths(SERIF, title, 24, 56, 36, WHITE)
    meta_paths, _ = text_paths_right(MONO_MED, meta, 11, 1344, 35, SKY, letter_spacing=0.8)
    body = f'''
  {PANEL_CSS}
  <rect class="panel-bg" width="{W}" height="{H}" fill="{BG}"/>
  <rect x="0" y="0" width="3" height="{H}" fill="{SKY}"/>
  <line x1="56" y1="{H}" x2="1344" y2="{H}" stroke="{LINE}" stroke-opacity="0.22" stroke-width="1"/>
  {title_paths}
  {meta_paths}
'''
    save_svg(ASSETS / filename, W, H, body, alt)


def main() -> None:
    for item in RAILS:
        build_rail(*item)


if __name__ == "__main__":
    main()
