#!/usr/bin/env python3
"""Build the profile dashboard from public GitHub activity and a static avatar portrait."""

import datetime as dt
import html
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
PORTRAIT = ROOT / "assets" / "avatar-ascii.txt"

BG = "#0d1117"
PANEL = "#10151d"
CARD = "#161b22"
LINE = "#30363d"
WHITE = "#e6edf3"
MUTED = "#8b949e"
GREEN = "#3fb950"
DIM_GREEN = "#238636"
RAMP = ["#161f22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
MONO = "Consolas,Menlo,monospace"


def esc(value):
    return html.escape(str(value), quote=True)


def short(date_string):
    if not date_string:
        return "—"
    day = dt.date.fromisoformat(date_string)
    return f"{day:%b} {day.day}"


def streak_range(streak):
    if not streak["length"]:
        return "Start a new run"
    if streak["start"] == streak["end"]:
        return short(streak["end"])
    return f'{short(streak["start"])} – {short(streak["end"])}'


def rect(x, y, w, h, fill, radius=0, stroke=None, more=""):
    border = f' stroke="{stroke}"' if stroke else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="{fill}"{border} {more}/>')


def label(x, y, content, size=14, color=WHITE, weight=400, anchor="start", more=""):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-family="{MONO}" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'{more}>{esc(content)}</text>')


def grid_for(days):
    """Sunday-first calendar columns, including the partial first and last weeks."""
    columns = []
    first = dt.date.fromisoformat(days[0]["date"])
    column = [None] * ((first.weekday() + 1) % 7)
    for day in days:
        date = dt.date.fromisoformat(day["date"])
        weekday = (date.weekday() + 1) % 7
        while len(column) < weekday:
            column.append(None)
        column.append(day)
        if len(column) == 7:
            columns.append(column)
            column = []
    if column:
        columns.append(column + [None] * (7 - len(column)))
    return columns


def level(day):
    count = day["count"]
    if count == 0:
        return 0
    if count <= 5:
        return 1
    if count <= 15:
        return 2
    if count <= 30:
        return 3
    if count <= 50:
        return 4
    return 5


def heatmap(parts, data, mobile):
    columns = grid_for(data["days"])
    if mobile:
        columns = columns[-26:]
    x0, y0, step, cell = (47, 54, 16, 13) if mobile else (63, 52, 18, 15)
    seen = set()
    months = []
    for ci, column in enumerate(columns):
        for day in column:
            if day:
                date = dt.date.fromisoformat(day["date"])
                month = (date.year, date.month)
                if month not in seen:
                    seen.add(month)
                    months.append((ci, date.strftime("%b")))
                break
        for ri, day in enumerate(column):
            if day is None:
                continue
            x, y = x0 + ci * step, y0 + ri * step
            delay = ci * (0.022 if mobile else 0.012) + ri * 0.015
            count = day["count"]
            suffix = "" if count == 1 else "s"
            parts.append(
                f'<rect class="cell" x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'rx="3" fill="{RAMP[level(day)]}" style="animation-delay:{delay:.3f}s">'
                f'<title>{day["date"]}: {count} contribution{suffix}</title></rect>'
            )
    for index, (ci, month) in enumerate(months):
        if index + 1 < len(months) and months[index + 1][0] - ci < 3:
            continue
        parts.append(label(x0 + ci * step, y0 - 16, month,
                           11 if mobile else 13, MUTED, 600))
    for row, text in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(label(25 if mobile else 24, y0 + row * step + cell - 3,
                           text, 11 if mobile else 13, MUTED))
    summary_y = 198 if mobile else 218
    parts.append(label(x0, summary_y,
                       f'{data["total_contributions"]:,} contributions in the last year',
                       16 if mobile else 19, WHITE, 700))
    if mobile:
        parts.append(label(468, summary_y, "RECENT 26 WEEKS", 10, MUTED, 500, "end"))


def terminal_frame(parts, x, y, width, height, command):
    parts.append(rect(x, y, width, height, PANEL, 8, LINE))
    parts.append(f'<path d="M{x} {y+33}H{x+width}" stroke="{LINE}"/>')
    for i, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        parts.append(f'<circle cx="{x+16+i*11}" cy="{y+17}" r="3" fill="{color}"/>')
    parts.append(label(x + width / 2, y + 21, command, 10, MUTED, 400, "middle"))


def portrait(parts, data, mobile):
    x, y, width, height = (15, 289, 470, 555) if mobile else (24, 324, 516, 646)
    terminal_frame(parts, x, y, width, height,
                   f'{data["username"]}@github:~$ ./portrait.sh')
    lines = PORTRAIT.read_text(encoding="utf-8-sig").splitlines()
    baseline = y + (55 if mobile else 62)
    line_step = 9.0 if mobile else 10.35
    text_x = x + (36 if mobile else 36)
    font_size = 8.6 if mobile else 9.3
    for row, line in enumerate(lines):
        if not line.strip():
            continue
        delay = 0.30 + row * 0.025
        parts.append(
            f'<text class="portrait-line" x="{text_x}" y="{baseline+row*line_step:.1f}" '
            f'fill="{WHITE}" opacity="0.82" font-family="{MONO}" font-size="{font_size}" '
            f'xml:space="preserve" style="animation-delay:{delay:.3f}s">'
            f'{esc(line)}</text>'
        )
    footer_y = y + height - 41
    parts.append(f'<path d="M{x} {footer_y}H{x+width}" stroke="{LINE}"/>')
    parts.append(label(x + 15, footer_y + 26,
                       "NIDHIN NARAYANAN  /  TESTING ENGINEER",
                       11 if mobile else 12, WHITE, 700))
    parts.append(label(x + width - 15, footer_y + 26, "WEBANDCRAFTS",
                       9 if mobile else 10, MUTED, 500, "end"))


def metrics(data):
    active = data["active_days"]
    return [
        ("$ current streak", str(data["current_streak"]["length"]),
         "days", streak_range(data["current_streak"]), GREEN),
        ("$ longest streak", str(data["longest_streak"]["length"]),
         "days", streak_range(data["longest_streak"]), WHITE),
        ("$ contributions", f'{data["total_contributions"]:,}',
         "", "in the last year", WHITE),
        ("$ active days", str(active),
         "days", "in the last year", WHITE),
        ("$ best day", str(data["best_day"]["count"]),
         "", short(data["best_day"]["date"]), WHITE),
        ("$ avg / active day", f'{data["avg_per_active_day"]:.1f}',
         "", "contributions", WHITE),
    ]


def stats(parts, data, mobile):
    x, y, width, height = (15, 860, 470, 620) if mobile else (558, 324, 518, 646)
    terminal_frame(parts, x, y, width, height,
                   f'{data["username"]}@github:~$ ./stats.sh')
    pad, gap = (15, 11) if mobile else (16, 10)
    tile_width = (width - 2 * pad - gap) / 2
    tile_height = 91 if mobile else 96
    start_y = y + 43
    for index, (name, value, unit, caption, color) in enumerate(metrics(data)):
        col, row = index % 2, index // 2
        tx = x + pad + col * (tile_width + gap)
        ty = start_y + row * (tile_height + 9)
        delay = 0.20 + index * 0.10
        parts.append(f'<g class="metric" style="animation-delay:{delay:.2f}s">')
        parts.append(rect(tx, ty, tile_width, tile_height, CARD, 7, LINE))
        parts.append(label(tx + 12, ty + 22, name,
                           12 if mobile else 13, MUTED, 500))
        parts.append(label(tx + 12, ty + 60, value,
                           32 if len(value) <= 4 else 28, color, 800))
        # Keep the unit clear of the number even when the count grows.
        unit_x = tx + 16 + min(len(value), 7) * (20 if len(value) <= 4 else 17)
        if unit:
            parts.append(label(unit_x, ty + 58, unit, 12, MUTED, 400))
        parts.append(label(tx + 12, ty + tile_height - 11, caption, 11, MUTED))
        parts.append('</g>')
    chart_y = start_y + 3 * (tile_height + 9) + 1
    chart_h = y + height - chart_y - 16
    chart_x = x + pad
    chart_w = width - 2 * pad
    parts.append(rect(chart_x, chart_y, chart_w, chart_h, CARD, 7, LINE))
    parts.append(label(chart_x + 14, chart_y + 25, "$ contributions / month",
                       12 if mobile else 13, MUTED, 500))
    monthly = data["monthly"][-13:]
    highest = max((m["total"] for m in monthly), default=1) or 1
    bar_base = chart_y + chart_h - 62
    max_h = chart_h - 115
    bar_gap = (chart_w - 40) / len(monthly)
    bar_width = 17 if mobile else 22
    for index, month in enumerate(monthly):
        center = chart_x + 20 + (index + 0.5) * bar_gap
        total = month["total"]
        bar_h = max(3, round(max_h * total / highest)) if total else 2
        bx = center - bar_width / 2
        by = bar_base - bar_h
        color = GREEN if total else "#303a43"
        parts.append(rect(f'{bx:.1f}', f'{by:.1f}', bar_width, bar_h, color, 2,
                          more=f'class="bar" style="animation-delay:{0.55+index*0.055:.2f}s"'))
        if total and (total >= highest * 0.12 or total == highest):
            parts.append(label(f'{center:.1f}', by - 7, str(total), 10, WHITE, 700, "middle"))
        month_letter = dt.date.fromisoformat(month["month"] + "-01").strftime("%b")[0]
        parts.append(label(f'{center:.1f}', bar_base + 19, month_letter, 11, MUTED, 500, "middle"))
    parts.append(label(chart_x + 14, chart_y + chart_h - 10,
                       "REAL PUBLIC GITHUB ACTIVITY", 9, MUTED))
    parts.append(label(chart_x + chart_w - 14, chart_y + chart_h - 10,
                       "UPDATED DAILY", 9, MUTED, 400, "end"))


def render(data, mobile=False):
    width, height = (500, 1496) if mobile else (1100, 994)
    username = esc(data["username"])
    css = """
    @keyframes cell-in { from {opacity:0;transform:translateY(-6px)} to {opacity:1;transform:translateY(0)} }
    @keyframes line-in { from {opacity:0;transform:translateY(4px)} to {opacity:.82;transform:translateY(0)} }
    @keyframes rise-in { from {opacity:0;transform:translateY(12px)} to {opacity:1;transform:translateY(0)} }
    @keyframes bar-in { from {opacity:0;transform:scaleY(0)} to {opacity:1;transform:scaleY(1)} }
    .cell {animation:cell-in .38s ease-out both}
    .portrait-line {animation:line-in .38s ease-out both}
    .metric {animation:rise-in .55s ease-out both}
    .bar {transform-box:fill-box;transform-origin:center bottom;animation:bar-in .72s ease-out both}
    @media (prefers-reduced-motion:reduce) {
      .cell,.portrait-line,.metric,.bar {animation:none}
    }
    """
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        f'<title>Nidhin Narayanan — GitHub profile dashboard</title>',
        f'<desc>Real GitHub contribution calendar and statistics for {username}, '
        f'with a text portrait based on Nidhin’s GitHub avatar.</desc>',
        f'<style>{css}</style>',
        rect(0, 0, width, height, BG),
    ]
    heatmap(parts, data, mobile)
    pill_x, pill_y, pill_w = (63, 232, 374) if mobile else (354, 259, 392)
    parts.append(rect(pill_x, pill_y, pill_w, 42, CARD, 8))
    parts.append(label(width / 2, pill_y + 28,
                       f'{data["username"]}@github ~ $ whoami',
                       20 if mobile else 23, WHITE, 800, "middle"))
    portrait(parts, data, mobile)
    stats(parts, data, mobile)
    parts.append('</svg>')
    return ''.join(parts)


if __name__ == "__main__":
    with DATA.open(encoding="utf-8") as file:
        data = json.load(file)
    for mobile, name in ((False, "dashboard.svg"), (True, "dashboard-mobile.svg")):
        target = ROOT / name
        target.write_text(render(data, mobile), encoding="utf-8")
        print(f"wrote {target.name} ({target.stat().st_size // 1024} KB)")
