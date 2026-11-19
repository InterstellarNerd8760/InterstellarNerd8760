#!/usr/bin/env python3
"""Inject subtle SMIL + CSS motion into the existing header.svg."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgtype import MONO_MED, measure

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "assets" / "header.svg"

# Positions from the original header builder
KICKER = "SOFTWARE    /    RADIO    /    AEROSPACE"
KICKER_X = 56
KICKER_SIZE = 12.5
KICKER_TRACK = 3.5


def starfield() -> str:
    # Deterministic, mostly in the dark left/upper field so type stays readable
    seeds = [
        (92, 118, 1.1, 5.5, 0.2),
        (148, 96, 0.8, 7.0, 1.1),
        (214, 154, 1.0, 8.5, 2.4),
        (268, 88, 0.7, 6.2, 0.6),
        (330, 132, 0.9, 9.0, 3.2),
        (402, 74, 0.7, 7.8, 1.8),
        (188, 210, 0.6, 10.0, 4.0),
        (490, 108, 0.8, 6.8, 2.0),
        (74, 248, 0.7, 8.2, 0.9),
        (560, 64, 0.6, 9.4, 3.6),
        (620, 128, 0.8, 7.2, 1.4),
        (128, 300, 0.6, 11.0, 2.8),
        (300, 48, 0.9, 6.4, 0.3),
        (448, 168, 0.7, 8.8, 4.5),
        (710, 92, 0.6, 10.5, 2.2),
        (840, 58, 0.7, 7.6, 1.0),
        (980, 44, 0.8, 9.2, 3.8),
        (1180, 72, 0.7, 8.0, 0.5),
        (1260, 120, 0.6, 11.5, 2.6),
        (360, 250, 0.5, 12.0, 5.0),
        (52, 180, 0.8, 6.6, 1.6),
        (990, 200, 0.5, 13.0, 4.2),
        (1120, 48, 0.6, 8.4, 0.8),
        (240, 40, 0.7, 7.4, 3.0),
    ]
    parts = ['  <g id="stars" fill="#f2f5f8">']
    for i, (x, y, r, dur, delay) in enumerate(seeds):
        drift = 8 + (i % 5) * 1.5
        parts.append(
            f'''    <circle cx="{x}" cy="{y}" r="{r}" opacity="0.35">
      <animate class="motion" attributeName="opacity" values="0.12;0.7;0.12" dur="{dur}s" begin="{delay}s" repeatCount="indefinite"/>
    </circle>
    <g class="motion">
      <circle cx="{x}" cy="{y}" r="{r}" fill="#f2f5f8" opacity="0">
        <animateTransform attributeName="transform" type="translate" values="0 0; 0 -{drift:.1f}; 0 0" dur="{dur * 2.6:.1f}s" begin="{delay}s" repeatCount="indefinite"/>
      </circle>
    </g>'''
        )
    parts.append("  </g>")
    return "\n".join(parts)


def orbit() -> str:
    # Elliptical satellite track over the earth, on the right half
    cx, cy, rx, ry = 1088, 268, 248, 96
    path = f"M{cx + rx},{cy} A{rx},{ry} 0 1,1 {cx - rx},{cy} A{rx},{ry} 0 1,1 {cx + rx},{cy}"
    return f'''  <g id="orbit" fill="none" transform-origin="{cx} {cy}">
    <path id="orbitPath" d="{path}" stroke="#5cc8f5" stroke-opacity="0.28" stroke-width="1.1" stroke-dasharray="2.5 7"/>
    <g class="motion">
      <circle r="3.2" fill="#5cc8f5">
        <animateMotion dur="22s" repeatCount="indefinite" rotate="0">
          <mpath xlink:href="#orbitPath"/>
        </animateMotion>
      </circle>
      <circle r="8" fill="#5cc8f5" fill-opacity="0.16">
        <animateMotion dur="22s" repeatCount="indefinite" rotate="0">
          <mpath xlink:href="#orbitPath"/>
        </animateMotion>
      </circle>
    </g>
  </g>'''


def shimmer_and_caret() -> str:
    kicker_w = measure(MONO_MED, KICKER, KICKER_SIZE, KICKER_TRACK)
    caret_x = KICKER_X + kicker_w + 10
    caret_y = 186
    return f'''  <rect class="motion" x="0" y="0" width="160" height="2" fill="#f2f5f8" opacity="0">
    <animate attributeName="x" values="-160;1400" dur="7s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0;0.7;0.7;0" keyTimes="0;0.08;0.22;0.35" dur="7s" repeatCount="indefinite"/>
  </rect>
  <rect class="motion" x="{caret_x:.1f}" y="{caret_y}" width="8" height="2" fill="#5cc8f5">
    <animate attributeName="opacity" values="1;1;0;0" dur="1.2s" repeatCount="indefinite"/>
  </rect>'''


STYLE = '''  <style>
    @media (prefers-reduced-motion: reduce) {
      .motion { display: none !important; }
    }
    /* CSS motion for when the SVG is opened directly. GitHub serves this
       file as an image, where SMIL on the same elements is what actually runs. */
    @keyframes drift {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-8px); }
    }
    @keyframes pulse {
      0%, 100% { opacity: 0.2; }
      50% { opacity: 0.75; }
    }
    @keyframes orbit-spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
  </style>
'''


def main() -> None:
    svg = HEADER.read_text()
    # Idempotent: strip a previous injection
    svg = re.sub(r"\n  <!-- readme-motion -->.*?\n  <!-- /readme-motion -->", "", svg, flags=re.S)
    # Drop a previously injected style in defs if re-run after a partial write
    if "readme-motion" in svg:
        raise SystemExit("motion markers in an unexpected place; aborting")

    motion = (
        "  <!-- readme-motion -->\n"
        + STYLE
        + starfield()
        + "\n"
        + orbit()
        + "\n"
        + shimmer_and_caret()
        + "\n  <!-- /readme-motion -->\n"
    )

    # Place after the background image (and the 2px sky rule), before typography
    needle = 'preserveAspectRatio="xMidYMid slice"/>\n  <rect x="0" y="0" width="1400" height="2" fill="#5cc8f5"/>\n'
    if needle not in svg:
        raise SystemExit("header.svg does not match the expected background markup")
    # Keep the static sky rule, add motion after it
    svg = svg.replace(
        needle,
        needle + motion,
        1,
    )
    HEADER.write_text(svg)
    print(f"updated {HEADER} ({HEADER.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
