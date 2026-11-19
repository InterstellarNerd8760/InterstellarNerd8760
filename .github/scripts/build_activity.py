#!/usr/bin/env python3
"""Generate assets/activity.svg from public GitHub API data only."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgtype import (
    BG,
    LINE,
    MONO_MED,
    MONO_REG,
    PANEL_CSS,
    SAGE,
    SERIF,
    SKY,
    SURFACE,
    TEXT,
    TEXT2,
    TEXT3,
    WHITE,
    ellipsize,
    measure,
    save_svg,
    text_paths,
    text_paths_right,
)

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
OWNER = os.environ.get("GITHUB_REPOSITORY", "InterstellarNerd8760/InterstellarNerd8760").split("/")[0]
PT = ZoneInfo("America/Los_Angeles")
API = "https://api.github.com"
W = 1400
# Featured project last-push rows, only if the public repo exists
FEATURED = (
    ("lunar-atlas", "Lunar Atlas"),
    ("personal-site", "westonrosch.com"),
    ("WALL-E1", "WALL-E1"),
)

# Distinct colors from the site palette, reused in a fixed language order
LANG_COLORS = {
    "HTML": SKY,
    "JavaScript": "#7ec8e8",
    "TypeScript": SAGE,
    "Python": "#c9d3de",
    "CSS": "#4b5d73",
    "Jupyter Notebook": "#8fb4c8",
}


class GitHub:
    def __init__(self) -> None:
        self.token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    def get(self, path: str, params: dict | None = None):
        qs = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = path if path.startswith("http") else f"{API}{path}{qs}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "InterstellarNerd8760-readme-activity",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.loads(res.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode()[:400]
            raise SystemExit(f"GitHub API error {exc.code} for {url}: {detail}") from exc


def fmt_pt(dt: datetime) -> str:
    local = dt.astimezone(PT)
    # Nov 19, 2026, 12:20 PM PT
    return local.strftime("%b %-d, %Y, %-I:%M %p PT").replace("AM", "AM").replace("PM", "PM")


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def collect(gh: GitHub) -> dict:
    user = gh.get(f"/users/{OWNER}")
    repos = []
    page = 1
    while True:
        chunk = gh.get(
            f"/users/{OWNER}/repos",
            {"type": "owner", "per_page": 100, "page": page, "sort": "updated"},
        )
        if not chunk:
            break
        repos.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1

    public = [r for r in repos if not r.get("private") and not r.get("fork")]
    languages: dict[str, int] = defaultdict(int)
    latest_commits = []
    featured_push = {}

    for repo in public:
        name = repo["name"]
        langs = gh.get(f"/repos/{OWNER}/{name}/languages")
        for lang, bytes_ in langs.items():
            languages[lang] += int(bytes_)
        commits = gh.get(
            f"/repos/{OWNER}/{name}/commits",
            {"per_page": 5, "sha": repo.get("default_branch") or "main"},
        )
        if isinstance(commits, dict) and commits.get("message"):
            # empty repo or error-shaped body
            continue
        for c in commits:
            date = parse_dt(c["commit"]["author"]["date"])
            msg = c["commit"]["message"].split("\n", 1)[0].strip()
            latest_commits.append(
                {
                    "repo": name,
                    "sha": c["sha"][:7],
                    "date": date,
                    "msg": msg,
                }
            )
        if name in {row[0] for row in FEATURED} and repo.get("pushed_at"):
            featured_push[name] = parse_dt(repo["pushed_at"])

    latest_commits.sort(key=lambda c: c["date"], reverse=True)
    # Unique-enough recent work: keep the newest 5, skipping empty messages
    recent = [c for c in latest_commits if c["msg"]][:5]
    total_bytes = sum(languages.values())
    lang_rows = sorted(languages.items(), key=lambda kv: kv[1], reverse=True)

    return {
        "public_repos": int(user["public_repos"]),
        "languages": lang_rows,
        "total_bytes": total_bytes,
        "recent": recent,
        "featured_push": featured_push,
        "generated_at": datetime.now(timezone.utc),
    }


def bar_segments(lang_rows: list[tuple[str, int]], total: int, x: float, y: float, width: float, height: float) -> str:
    if total <= 0 or not lang_rows:
        return ""
    parts = []
    cursor = x
    for i, (name, n) in enumerate(lang_rows):
        w = width * (n / total)
        if w < 0.5:
            continue
        color = LANG_COLORS.get(name, LINE)
        # last segment should land exactly on the end to avoid a gap
        if i == len(lang_rows) - 1:
            w = x + width - cursor
        parts.append(
            f'<rect x="{cursor:.2f}" y="{y}" width="{w:.2f}" height="{height}" fill="{color}"/>'
        )
        cursor += w
    return "\n    ".join(parts)


def legend(lang_rows: list[tuple[str, int]], total: int, x: float, y: float) -> str:
    parts = []
    cursor = x
    for name, n in lang_rows:
        if total <= 0:
            continue
        pct = 100.0 * n / total
        # skip slivers that would just add noise
        if pct < 1.5 and name not in LANG_COLORS:
            continue
        label = f"{name}  {pct:.0f}%"
        color = LANG_COLORS.get(name, LINE)
        swatch = f'<rect x="{cursor:.1f}" y="{y - 8}" width="8" height="8" fill="{color}"/>'
        paths, w = text_paths(MONO_REG, label, 11, cursor + 14, y, TEXT2)
        parts.append(swatch + "\n    " + paths)
        cursor += 14 + w + 22
        if cursor > 1280:
            break
    return "\n    ".join(parts)


def build_svg(data: dict) -> None:
    public_repos = data["public_repos"]
    generated = fmt_pt(data["generated_at"])
    recent = data["recent"]
    featured = data["featured_push"]

    # Layout
    # header 0-70, stats + bar 70-150, featured + commits 150-end
    y = 0
    kicker, _ = text_paths(MONO_MED, "SIGNAL", 12, 56, 36, SKY, letter_spacing=3.4)
    kicker_w = measure(MONO_MED, "SIGNAL", 12, 3.4)
    title, _ = text_paths(SERIF, "From the public repos.", 28, 56, 78, WHITE)
    updated, _ = text_paths_right(MONO_REG, f"Updated {generated}", 11, 1344, 36, TEXT3, letter_spacing=0.3)

    # live dot by the kicker
    dot_x = 56 + kicker_w + 16
    live_dot = f'''<g>
    <circle cx="{dot_x}" cy="32" r="3.2" fill="{SKY}"/>
    <circle class="motion" cx="{dot_x}" cy="32" r="3.2" fill="{SKY}" fill-opacity="0.4">
      <animate attributeName="r" values="3.2;9;3.2" dur="2.4s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0.5;0;0.5" dur="2.4s" repeatCount="indefinite"/>
    </circle>
  </g>'''

    repo_label = f"{public_repos} public repositories"
    repo_p, _ = text_paths(MONO_MED, repo_label, 13, 56, 118, WHITE, letter_spacing=0.2)

    bar = bar_segments(data["languages"], data["total_bytes"], 56, 138, 1288, 8)
    # rounded-ish end caps via a clip? keep a simple bar with a hairline frame
    bar_frame = f'<rect x="56" y="138" width="1288" height="8" fill="none" stroke="{LINE}" stroke-opacity="0.25"/>'
    lang_legend = legend(data["languages"], data["total_bytes"], 56, 172)
    caption, _ = text_paths(
        MONO_REG,
        "Language share is source bytes in public, non-fork repositories.",
        10,
        56,
        196,
        TEXT3,
    )

    # Featured last-push row
    feat_kicker, _ = text_paths(MONO_MED, "LAST PUSH", 11, 56, 232, SKY, letter_spacing=2.2)
    feat_bits = []
    fx = 56
    fy = 260
    for repo_id, label in FEATURED:
        dt = featured.get(repo_id)
        if not dt:
            continue
        # compact: "Lunar Atlas  Nov 15, 2026"
        local = dt.astimezone(PT)
        date_s = local.strftime("%b %-d, %Y")
        block, w1 = text_paths(MONO_MED, label, 13, fx, fy, WHITE)
        date_p, w2 = text_paths(MONO_REG, date_s, 13, fx + w1 + 12, fy, TEXT2)
        feat_bits.append(block + "\n    " + date_p)
        fx += w1 + 12 + w2 + 36
    feat_markup = "\n    ".join(feat_bits)

    # Recent commits
    rec_kicker, _ = text_paths(MONO_MED, "RECENT COMMITS", 11, 56, 300, SKY, letter_spacing=2.2)
    rows = []
    row_y = 328
    for c in recent:
        local = c["date"].astimezone(PT)
        date_s = local.strftime("%b %-d, %-I:%M %p PT")
        repo_s = ellipsize(MONO_MED, c["repo"], 13, 230)
        repo_p, rw = text_paths(MONO_MED, repo_s, 13, 56, row_y, SKY)
        date_p, dw = text_paths_right(MONO_REG, date_s, 12, 1344, row_y, TEXT3)
        date_w = measure(MONO_REG, date_s, 12)
        msg = ellipsize(MONO_REG, c["msg"], 13, 1344 - 56 - 250 - date_w - 40)
        msg_p, _ = text_paths(MONO_REG, msg, 13, 56 + 250, row_y, TEXT)
        rows.append(repo_p + "\n    " + msg_p + "\n    " + date_p)
        row_y += 32

    height = row_y + 28
    body = f'''
  {PANEL_CSS}
  <rect class="panel-bg" width="{W}" height="{height}" fill="{BG}"/>
  <rect x="0" y="0" width="3" height="{height}" fill="{SKY}"/>
  <line x1="56" y1="18" x2="1344" y2="18" stroke="{LINE}" stroke-opacity="0.18" stroke-width="1"/>
  {kicker}
  {live_dot}
  {updated}
  {title}
  {repo_p}
  {bar_frame}
  {bar}
  {lang_legend}
  {caption}
  <line x1="56" y1="214" x2="1344" y2="214" stroke="{LINE}" stroke-opacity="0.14" stroke-width="1"/>
  {feat_kicker}
  {feat_markup}
  {rec_kicker}
  {chr(10).join(rows)}
'''
    alt = (
        f"{public_repos} public repositories. "
        f"Activity panel updated {generated}."
    )
    save_svg(ASSETS / "activity.svg", W, height, body, alt)


def main() -> None:
    gh = GitHub()
    data = collect(gh)
    build_svg(data)


if __name__ == "__main__":
    main()
