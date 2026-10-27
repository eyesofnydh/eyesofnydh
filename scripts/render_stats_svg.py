#!/usr/bin/env python3
"""Render a compact, readable GitHub activity card from contribution data."""

import datetime
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "data", "contributions.json")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "stats.svg")

W, H = 840, 540
PAD, GAP = 26, 18
TILE_W = (W - 2 * PAD - GAP) / 2
TILE_H = 164
TILES_TOP = 112
BG = "#09131c"
TILE = "#10212b"
BORDER = "#2b4c50"
TEXT = "#f2fbfa"
MUTED = "#9abbbd"
GREEN = "#39d353"
CYAN = "#4fe1d7"


def short(date_string):
    day = datetime.date.fromisoformat(date_string)
    return f"{day:%b} {day.day}"


def streak_caption(streak):
    if not streak["length"] or not streak["start"] or not streak["end"]:
        return "Your next run starts here"
    if streak["start"] == streak["end"]:
        return short(streak["end"])
    return f'{short(streak["start"])} – {short(streak["end"])}'


def render(data):
    username = html.escape(data["username"])
    current = data["current_streak"]
    longest = data["longest_streak"]
    best = data["best_day"]
    tiles = [
        ("01 / CONTRIBUTIONS", data["total_contributions"], "", "in the last year", GREEN),
        ("02 / CURRENT STREAK", current["length"], "day" if current["length"] == 1 else "days", streak_caption(current), CYAN),
        ("03 / ACTIVE DAYS", data["active_days"], "days", "in the last year", CYAN),
        ("04 / LONGEST STREAK", longest["length"], "day" if longest["length"] == 1 else "days", streak_caption(longest), GREEN),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
        f'<title>GitHub activity for {username}</title>',
        f'<desc>{data["total_contributions"]} contributions, {data["active_days"]} active days, '
        f'{current["length"]} day current streak, {longest["length"]} day longest streak.</desc>',
        '<style>.tile{animation:rise .5s ease-out both}'
        '@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}'
        '@media (prefers-reduced-motion:reduce){.tile{animation:none}}</style>',
        '<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#09131c"/>'
        '<stop offset="1" stop-color="#0b2730"/></linearGradient></defs>',
        f'<rect width="{W}" height="{H}" rx="18" fill="url(#bg)"/>',
        f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17" fill="none" stroke="{BORDER}"/>',
        f'<path d="M0 44H{W}" stroke="{BORDER}"/>',
    ]
    for i, color in enumerate(("#ff6b6b", "#f5c451", "#39d353")):
        parts.append(f'<circle cx="{PAD + i * 17}" cy="22" r="5" fill="{color}"/>')
    parts.extend([
        f'<text x="{W/2}" y="28" fill="{MUTED}" text-anchor="middle" '
        f'font-family="Consolas,Menlo,monospace" font-size="14">{username}@github:~$ ./stats</text>',
        f'<text x="{PAD}" y="88" fill="{TEXT}" font-family="Segoe UI,Arial,sans-serif" '
        'font-size="30" font-weight="800">THE NUMBERS</text>',
        f'<text x="{W-PAD}" y="86" fill="{CYAN}" text-anchor="end" '
        'font-family="Consolas,Menlo,monospace" font-size="15">LIVE GITHUB DATA</text>',
    ])
    for index, (label, value, unit, caption, accent) in enumerate(tiles):
        col, row = index % 2, index // 2
        x = PAD + col * (TILE_W + GAP)
        y = TILES_TOP + row * (TILE_H + GAP)
        font_size = 64 if len(f"{value:,}") > 5 else 72
        parts.extend([
            f'<g class="tile" style="animation-delay:{index * .12:.2f}s">',
            f'<rect x="{x:.1f}" y="{y}" width="{TILE_W:.1f}" height="{TILE_H}" rx="14" fill="{TILE}" stroke="{BORDER}"/>',
            f'<rect x="{x:.1f}" y="{y+18}" width="4" height="{TILE_H-36}" rx="2" fill="{accent}"/>',
            f'<text x="{x+24:.1f}" y="{y+34}" fill="{MUTED}" font-family="Consolas,Menlo,monospace" '
            f'font-size="19">{label}</text>',
            f'<text x="{x+24:.1f}" y="{y+111}" fill="{TEXT}" font-family="Segoe UI,Arial,sans-serif" '
            f'font-size="{font_size}" font-weight="800">{value:,}'
            f'<tspan fill="{accent}" font-size="24" font-weight="600"> {unit}</tspan></text>',
            f'<text x="{x+24:.1f}" y="{y+143}" fill="{MUTED}" font-family="Segoe UI,Arial,sans-serif" '
            f'font-size="19">{html.escape(caption)}</text>',
            '</g>',
        ])
    best_caption = f'{best["count"]} contribution' + ('' if best["count"] == 1 else 's')
    parts.extend([
        f'<path d="M{PAD} 486H{W-PAD}" stroke="{BORDER}"/>',
        f'<text x="{PAD}" y="516" fill="{MUTED}" font-family="Consolas,Menlo,monospace" font-size="16">'
        f'BEST DAY <tspan fill="{GREEN}">{best_caption.upper()}</tspan> · {short(best["date"]).upper()}</text>',
        f'<text x="{W-PAD}" y="516" fill="{MUTED}" text-anchor="end" '
        'font-family="Consolas,Menlo,monospace" font-size="16">UPDATED DAILY</text>',
        '</svg>',
    ])
    return ''.join(parts)


if __name__ == "__main__":
    with open(SRC, encoding="utf-8") as source:
        data = json.load(source)
    svg = render(data)
    with open(OUT, "w", encoding="utf-8") as output:
        output.write(svg)
    print(f"wrote {OUT}: {W} x {H}, {len(svg)//1024} KB")
