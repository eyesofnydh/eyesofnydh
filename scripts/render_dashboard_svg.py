#!/usr/bin/env python3
"""Render a polished, animated GitHub profile visual from public activity data."""

import base64
import datetime as dt
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INK = "#0a1016"
SURFACE = "#101b22"
LINE = "#244049"
TEXT = "#f3f8f7"
MUTED = "#9ab4b8"
TEAL = "#55ddd0"
GREEN = "#48d870"
LIME = "#b4ef73"
CORAL = "#ff9b7e"
RAMP = ["#183039", "#164d3e", "#158056", "#22a662", "#36cd6d", "#7aec9b"]
SANS = "Segoe UI,Arial,sans-serif"
MONO = "Consolas,Menlo,monospace"


def e(value):
    return html.escape(str(value), quote=True)


def rect(x, y, w, h, fill, radius=0, stroke=None, extra=""):
    border = f' stroke="{stroke}"' if stroke else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="{fill}"{border} {extra}/>')


def text(x, y, value, size, color=TEXT, weight=400, family=SANS, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-family="{family}" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'{extra}>{e(value)}</text>')


def enter_text(parts, delay, *args):
    parts.append(text(*args, extra=f'class="enter" style="animation-delay:{delay:.2f}s"'))


def first_sunday(date):
    return date - dt.timedelta(days=(date.weekday() + 1) % 7)


def grid(days):
    weeks = []
    current = []
    last_start = None
    for day in days:
        date = dt.date.fromisoformat(day["date"])
        start = first_sunday(date)
        if start != last_start:
            if current:
                weeks.append(current)
            current = [None] * ((date.weekday() + 1) % 7)
            last_start = start
        current.append(day)
    if current:
        weeks.append(current + [None] * (7 - len(current)))
    return weeks


def intensity(day):
    count = day["count"]
    if count == 0:
        return 0
    if count <= 3:
        return 1
    if count <= 8:
        return 2
    if count <= 15:
        return 3
    if count <= 25:
        return 4
    return 5


def chrome(parts, x, y, width, command):
    parts.append(f'<path d="M{x} {y+42}H{x+width}" stroke="{LINE}"/>')
    for index, color in enumerate((CORAL, "#f8ca71", GREEN)):
        parts.append(f'<circle cx="{x+20+index*15}" cy="{y+21}" r="4" fill="{color}"/>')
    parts.append(text(x + width / 2, y + 27, command, 11, MUTED, 500, MONO, "middle"))


def heatmap(parts, data, mobile):
    weeks = grid(data["days"])
    if mobile:
        weeks = weeks[-26:]
    x0, y0, step, cell = (69, 165, 17, 13) if mobile else (81, 182, 20, 16)
    seen = set()
    month_labels = []
    clip_cells = []
    for index, week in enumerate(weeks):
        for day in week:
            if day:
                date = dt.date.fromisoformat(day["date"])
                key = (date.year, date.month)
                if key not in seen:
                    seen.add(key)
                    month_labels.append((index, date.strftime("%b").upper()))
                break
        for row, day in enumerate(week):
            if not day:
                continue
            x, y = x0 + index * step, y0 + row * step
            # A diagonal cascade builds the calendar from left to right.
            delay = 0.22 + index * (0.082 if mobile else 0.043) + row * 0.045
            count = day["count"]
            plural = "" if count == 1 else "s"
            clip_cells.append(rect(x, y, cell, cell, "white", 3))
            parts.append(
                f'<rect class="day" x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'rx="3" fill="{RAMP[intensity(day)]}" style="animation-delay:{delay:.3f}s">'
                f'<title>{day["date"]}: {count} contribution{plural}</title></rect>'
            )
    # The clip keeps the returning light sweep inside the actual calendar squares.
    parts.append('<defs><clipPath id="calendar-cells">' + ''.join(clip_cells) + '</clipPath></defs>')
    parts.append(
        f'<g clip-path="url(#calendar-cells)">'
        f'<rect class="sweep" x="{x0-180}" y="{y0}" width="180" height="{7*step}" '
        f'fill="url(#sweep-gradient)"/></g>'
    )
    for i, (index, month) in enumerate(month_labels):
        if i + 1 < len(month_labels) and month_labels[i + 1][0] - index < 3:
            continue
        parts.append(text(x0 + index * step, y0 - 13, month, 11, MUTED, 600, MONO))
    for row, name in ((1, "MON"), (3, "WED"), (5, "FRI")):
        parts.append(text(25 if mobile else 32, y0 + row * step + cell - 3,
                          name, 10 if mobile else 11, MUTED, 500, MONO))


def avatar(parts, encoded, x, y, size, clip_id):
    parts.append(f'<clipPath id="{clip_id}">{rect(x, y, size, size, "white", 18)}</clipPath>')
    parts.append(rect(x-2, y-2, size+4, size+4, "none", 20, LINE))
    parts.append(
        f'<image class="avatar" x="{x}" y="{y}" width="{size}" height="{size}" '
        f'clip-path="url(#{clip_id})" href="data:image/jpeg;base64,{encoded}" '
        f'preserveAspectRatio="xMidYMid meet" style="image-rendering:pixelated"/>'
    )
    parts.append(rect(x+size-117, y+size-42, 103, 27, INK, 7, TEAL))
    parts.append(text(x+size-65, y+size-24, "NN // 01", 12, TEAL, 700, MONO, "middle"))


def metric(parts, x, y, w, label, value, note, index, highlight=False, mobile=False):
    parts.append(f'<g class="metric" style="animation-delay:{1.35+index*0.16:.2f}s">')
    parts.append(rect(x, y, w, 91 if mobile else 82, SURFACE, 11, LINE))
    parts.append(rect(x, y, 4, 91 if mobile else 82, GREEN if highlight else TEAL, 2))
    parts.append(text(x + 19, y + 25, label.upper(), 11, MUTED, 700, MONO))
    parts.append(text(x + 19, y + (61 if mobile else 58), value, 30 if mobile else 28,
                      LIME if highlight else TEXT, 800))
    parts.append(text(x + w - 14, y + (59 if mobile else 55), note,
                      11 if mobile else 10, MUTED, 400, MONO, "end"))
    parts.append('</g>')


def weekly_bars(parts, data, x, y, width, height, mobile=False):
    parts.append('<g class="chart" style="animation-delay:1.9s">')
    parts.append(rect(x, y, width, height, SURFACE, 13, LINE))
    parts.append(text(x + 20, y + 30, "THE RECENT RUN", 13, TEXT, 800, MONO))
    parts.append(text(x + width - 20, y + 30, "LAST 12 WEEKS", 11, MUTED, 600, MONO, "end"))
    weeks = grid(data["days"])[-12:]
    totals = [sum(day["count"] for day in week if day) for week in weeks]
    max_total = max(totals) or 1
    base = y + height - 34
    max_height = height - 78
    plot_left = x + 22
    step = (width - 44) / len(weeks)
    bar_width = 22 if mobile else 27
    for i, total in enumerate(totals):
        center = plot_left + (i + 0.5) * step
        bar_height = max(3, round(total / max_total * max_height)) if total else 2
        bx, by = center - bar_width / 2, base - bar_height
        color = GREEN if total else "#2b4148"
        parts.append(rect(f'{bx:.1f}', f'{by:.1f}', bar_width, bar_height, color, 4,
                          extra=f'class="bar" style="animation-delay:{2.15+i*0.10:.2f}s"'))
        if total and total >= max_total * 0.3:
            parts.append(text(f'{center:.1f}', by - 7, str(total), 10,
                              TEXT, 700, MONO, "middle",
                              f'class="enter" style="animation-delay:{2.25+i*0.10:.2f}s"'))
        if i in (0, 4, 8, 11):
            day = next((item["date"] for item in weeks[i] if item), None)
            if day:
                date = dt.date.fromisoformat(day)
                parts.append(text(f'{center:.1f}', base + 22, date.strftime("%b %d"),
                                  10, MUTED, 500, MONO, "middle"))
    parts.append('</g>')


def desktop(parts, data, encoded):
    w, h = 1200, 1080
    parts.append(rect(0, 0, w, h, "url(#background)", 25, LINE))
    parts.append(rect(0, 0, 7, h, "url(#edge)", 3))
    parts.append(f'<path d="M0 64H{w}" stroke="{LINE}"/>')
    parts.append(rect(42, 21, 25, 25, TEAL, 6))
    parts.append(text(54, 38, "N", 16, INK, 900, SANS, "middle"))
    enter_text(parts, 0.08, 80, 40, "NIDHIN  /  QUALITY ENGINEERING", 13, TEXT, 700, MONO)
    enter_text(parts, 0.12, 1150, 40, "GITHUB  ·  EYESOFNYDH", 12, MUTED, 600, MONO, "end")

    enter_text(parts, 0.16, 50, 119, "01 / ACTIVITY TIMELINE", 13, TEAL, 700, MONO)
    enter_text(parts, 0.20, 1150, 119, f'{data["total_contributions"]:,} CONTRIBUTIONS THIS YEAR',
               13, TEXT, 700, MONO, "end")
    heatmap(parts, data, False)
    parts.append(f'<path d="M50 342H1150" stroke="{LINE}"/>')

    px, py, pw, ph = 50, 373, 510, 657
    parts.append('<g class="panel" style="animation-delay:.68s">')
    parts.append(rect(px, py, pw, ph, SURFACE, 16, LINE))
    chrome(parts, px, py, pw, "eyesofnydh@github:~$ ./portrait")
    avatar(parts, encoded, px + 17, py + 59, 476, "portrait-desktop")
    parts.append(f'<path d="M{px} {py+570}H{px+pw}" stroke="{LINE}"/>')
    parts.append(text(px + 22, py + 605, "THE PERSON BEHIND THE TESTS", 13, TEAL, 700, MONO))
    parts.append(text(px + 22, py + 636, "Curious by default. Precise by practice.", 18, TEXT, 500))
    parts.append('</g>')

    rx = 605
    enter_text(parts, 0.64, rx, 401, "02 / WHO AM I", 13, TEAL, 700, MONO)
    enter_text(parts, 0.78, rx, 487, "Nidhin", 82, TEXT, 800)
    enter_text(parts, 0.92, rx, 572, "Narayanan", 72, TEXT, 800)
    parts.append(rect(rx, 593, 55, 5, CORAL, 2,
                      extra='class="enter" style="animation-delay:1.04s"'))
    enter_text(parts, 1.08, rx, 634, "Testing Engineer at Webandcrafts", 23, TEXT, 600)
    enter_text(parts, 1.20, rx, 669, "I find the cracks before release, then make", 17, MUTED, 400)
    enter_text(parts, 1.28, rx, 694, "the useful lessons repeatable.", 17, MUTED, 400)

    metric(parts, rx, 727, 260, "Contributions", f'{data["total_contributions"]:,}',
           "last year", 0, highlight=True)
    metric(parts, rx + 275, 727, 260, "Active days", str(data["active_days"]),
           "days", 1)
    metric(parts, rx, 820, 260, "Current streak", str(data["current_streak"]["length"]),
           "days", 2)
    metric(parts, rx + 275, 820, 260, "Longest streak", str(data["longest_streak"]["length"]),
           "days", 3)
    weekly_bars(parts, data, rx, 913, 535, 117)


def mobile(parts, data, encoded):
    w, h = 560, 1800
    parts.append(rect(0, 0, w, h, "url(#background)", 23, LINE))
    parts.append(rect(0, 0, 6, h, "url(#edge)", 3))
    parts.append(f'<path d="M0 64H{w}" stroke="{LINE}"/>')
    parts.append(rect(26, 21, 25, 25, TEAL, 6))
    parts.append(text(38, 38, "N", 16, INK, 900, SANS, "middle"))
    enter_text(parts, 0.08, 64, 40, "NIDHIN / QA", 13, TEXT, 700, MONO)
    enter_text(parts, 0.12, 534, 40, "GITHUB  ·  LIVE", 12, MUTED, 600, MONO, "end")

    enter_text(parts, 0.16, 28, 106, "01 / ACTIVITY TIMELINE", 12, TEAL, 700, MONO)
    enter_text(parts, 0.20, 533, 106, f'{data["total_contributions"]:,} THIS YEAR',
               12, TEXT, 700, MONO, "end")
    heatmap(parts, data, True)
    parts.append(text(69, 308, "RECENT 26 WEEKS  /  REAL PUBLIC ACTIVITY", 11, MUTED, 600, MONO))
    parts.append(f'<path d="M28 337H532" stroke="{LINE}"/>')

    enter_text(parts, 0.64, 30, 383, "02 / WHO AM I", 12, TEAL, 700, MONO)
    enter_text(parts, 0.78, 30, 454, "Nidhin", 73, TEXT, 800)
    enter_text(parts, 0.92, 30, 528, "Narayanan", 67, TEXT, 800)
    parts.append(rect(30, 549, 52, 5, CORAL, 2,
                      extra='class="enter" style="animation-delay:1.04s"'))
    enter_text(parts, 1.08, 30, 592, "Testing Engineer at Webandcrafts", 21, TEXT, 600)
    enter_text(parts, 1.20, 30, 627, "I find the cracks before release, then", 16, MUTED)
    enter_text(parts, 1.28, 30, 651, "make the useful lessons repeatable.", 16, MUTED)

    px, py, pw, ph = 30, 684, 500, 545
    parts.append('<g class="panel" style="animation-delay:.68s">')
    parts.append(rect(px, py, pw, ph, SURFACE, 16, LINE))
    chrome(parts, px, py, pw, "eyesofnydh@github:~$ ./portrait")
    avatar(parts, encoded, px + 16, py + 58, 468, "portrait-mobile")
    parts.append(f'<path d="M{px} {py+535}H{px+pw}" stroke="{LINE}"/>')
    parts.append('</g>')

    metric(parts, 30, 1255, 243, "Contributions", f'{data["total_contributions"]:,}',
           "last year", 0, highlight=True, mobile=True)
    metric(parts, 287, 1255, 243, "Active days", str(data["active_days"]),
           "days", 1, mobile=True)
    metric(parts, 30, 1359, 243, "Current streak", str(data["current_streak"]["length"]),
           "days", 2, mobile=True)
    metric(parts, 287, 1359, 243, "Longest streak", str(data["longest_streak"]["length"]),
           "days", 3, mobile=True)
    weekly_bars(parts, data, 30, 1480, 500, 273, True)


def render(data, encoded, mobile_view=False):
    w, h = (560, 1800) if mobile_view else (1200, 1080)
    travel = 802 if mobile_view else 1420
    css = f"""
      @keyframes reveal-day {{
        from {{opacity:0;transform:translateY(-11px) scale(.65)}}
        to {{opacity:1;transform:translateY(0) scale(1)}}
      }}
      @keyframes flow {{
        0% {{transform:translateX(0)}}
        58%,100% {{transform:translateX({travel}px)}}
      }}
      @keyframes enter {{
        from {{opacity:0;transform:translateY(18px)}}
        to {{opacity:1;transform:translateY(0)}}
      }}
      @keyframes portrait-in {{
        from {{opacity:0;transform:scale(1.08)}}
        to {{opacity:1;transform:scale(1)}}
      }}
      @keyframes grow {{
        from {{opacity:0;transform:scaleY(0)}}
        to {{opacity:1;transform:scaleY(1)}}
      }}
      .day {{transform-box:fill-box;transform-origin:center;animation:reveal-day .72s cubic-bezier(.16,1,.3,1) both}}
      .sweep {{animation:flow 13s cubic-bezier(.42,0,.58,1) 1.6s infinite both}}
      .enter,.panel,.chart {{animation:enter .75s cubic-bezier(.16,1,.3,1) both}}
      .avatar {{transform-box:fill-box;transform-origin:center;animation:portrait-in 1.25s cubic-bezier(.16,1,.3,1) .9s both}}
      .metric {{animation:enter .7s cubic-bezier(.16,1,.3,1) both}}
      .bar {{transform-box:fill-box;transform-origin:center bottom;animation:grow .85s cubic-bezier(.16,1,.3,1) both}}
      @media (prefers-reduced-motion:reduce) {{
        .day,.sweep,.enter,.panel,.chart,.avatar,.metric,.bar {{animation:none}}
      }}
    """
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img">',
        '<title>Nidhin Narayanan — quality engineer and GitHub activity</title>',
        f'<desc>Profile portrait and real GitHub activity for {e(data["username"])}: '
        f'{data["total_contributions"]:,} contributions and {data["active_days"]} active days.</desc>',
        f'<style>{css}</style>',
        '<defs>'
        '<radialGradient id="background" cx="78%" cy="20%" r="90%">'
        '<stop stop-color="#12333a"/><stop offset=".55" stop-color="#0d1b23"/>'
        '<stop offset="1" stop-color="#0a1016"/></radialGradient>'
        '<linearGradient id="edge" x2="0" y2="1">'
        '<stop stop-color="#55ddd0"/><stop offset=".52" stop-color="#48d870"/>'
        '<stop offset="1" stop-color="#ff9b7e"/></linearGradient>'
        '<linearGradient id="sweep-gradient" x1="0" y1="0" x2="1" y2="0">'
        '<stop stop-color="#39d353" stop-opacity="0"/>'
        '<stop offset=".35" stop-color="#39d353" stop-opacity=".10"/>'
        '<stop offset=".64" stop-color="#48e47b" stop-opacity=".56"/>'
        '<stop offset="1" stop-color="#39d353" stop-opacity="0"/></linearGradient>'
        '</defs>',
    ]
    if mobile_view:
        mobile(parts, data, encoded)
    else:
        desktop(parts, data, encoded)
    parts.append('</svg>')
    return ''.join(parts)


if __name__ == "__main__":
    data = json.loads((ROOT / "data" / "contributions.json").read_text(encoding="utf-8"))
    encoded_avatar = base64.b64encode((ROOT / "assets" / "avatar.jpg").read_bytes()).decode("ascii")
    for mobile_view, name in ((False, "dashboard.svg"), (True, "dashboard-mobile.svg")):
        output = ROOT / name
        output.write_text(render(data, encoded_avatar, mobile_view), encoding="utf-8")
        print(f"wrote {name} ({output.stat().st_size // 1024} KB)")
