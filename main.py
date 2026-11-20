#!/usr/bin/env python3
"""news-image-20261119, round 4: 'The World in One Day' - Thursday 19 Nov 2026.

A one-page newspaper front sheet summing up one day of world news.
Everything on the page is drawn as vector geometry in code: filled
polygons, circles and thick strokes for the illustrations, and a
stroke (polyline) typeface for every letter - no bitmap font, no
images, no external assets. The scene is rendered on a 4096x4096
canvas and box-downscaled to 1024x1024 so all edges are smooth.
Python standard library only. Fully deterministic.
"""

import math
import os
import zlib
import struct
from operator import add

# ---------------------------------------------------------------- canvas
SS = 4                      # supersampling factor
W = 1024                    # final width/height
W4 = W * SS                 # render width/height

PAPER = (247, 242, 231)     # warm cream paper
PANEL = (253, 250, 243)     # panel card
TINT = (240, 233, 216)      # art tint
INK = (27, 25, 21)          # near-black ink
GREY = (108, 100, 90)       # secondary ink
RULE = (198, 188, 168)      # hairlines
RED = (176, 32, 26)         # the one accent
BLUE = (52, 84, 122)
TEAL = (43, 108, 100)
GREEN = (57, 108, 57)
GOLD = (172, 124, 30)
BROWN = (122, 84, 52)
SKY = (196, 216, 228)
SEA = (84, 128, 164)
SAND = (216, 192, 148)
NAVY = (24, 30, 52)

FB = bytearray(bytes(PAPER) * (W4 * W4))


def _span(y, x0, x1, c):
    if y < 0 or y >= W4:
        return
    if x0 < 0:
        x0 = 0
    if x1 > W4 - 1:
        x1 = W4 - 1
    if x1 < x0:
        return
    off = y * W4 * 3 + x0 * 3
    FB[off:off + (x1 - x0 + 1) * 3] = bytes(c) * (x1 - x0 + 1)


def fill_rect(x, y, w, h, c):
    x0 = int(round(x * SS))
    y0 = int(round(y * SS))
    x1 = int(round((x + w) * SS)) - 1
    y1 = int(round((y + h) * SS)) - 1
    if x1 < x0 or y1 < y0:
        return
    row = bytes(c) * (x1 - x0 + 1)
    n = len(row)
    for yy in range(y0, y1 + 1):
        off = yy * W4 * 3 + x0 * 3
        FB[off:off + n] = row


def fill_circle(cx, cy, r, c):
    cx *= SS
    cy *= SS
    r *= SS
    y0 = int(cy - r)
    y1 = int(cy + r)
    r2 = r * r
    for yy in range(y0, y1 + 1):
        dy = yy - cy
        d2 = r2 - dy * dy
        if d2 < 0:
            continue
        dx = int(math.sqrt(d2))
        _span(yy, int(cx - dx), int(cx + dx), c)


def fill_ellipse(cx, cy, rx, ry, c):
    cx *= SS
    cy *= SS
    rx *= SS
    ry *= SS
    y0 = int(cy - ry)
    y1 = int(cy + ry)
    for yy in range(y0, y1 + 1):
        dy = (yy - cy) / ry
        d2 = 1.0 - dy * dy
        if d2 < 0:
            continue
        dx = int(rx * math.sqrt(d2))
        _span(yy, int(cx - dx), int(cx + dx), c)


def fill_poly(pts, c):
    P = [(x * SS, y * SS) for x, y in pts]
    ys = [p[1] for p in P]
    y0 = int(min(ys))
    y1 = int(max(ys))
    n = len(P)
    for yy in range(y0, y1 + 1):
        yc = yy + 0.5
        xs = []
        for i in range(n):
            x1, y1 = P[i]
            x2, y2 = P[(i + 1) % n]
            if (y1 <= yc < y2) or (y2 <= yc < y1):
                xs.append(x1 + (yc - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            _span(yy, int(xs[i]), int(xs[i + 1]), c)


def stroke_line(x1, y1, x2, y2, w, c):
    dx = x2 - x1
    dy = y2 - y1
    ln = math.hypot(dx, dy)
    if ln == 0:
        fill_circle(x1, y1, w / 2.0, c)
        return
    nx = -dy / ln * w / 2.0
    ny = dx / ln * w / 2.0
    fill_poly([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
               (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], c)
    fill_circle(x1, y1, w / 2.0, c)
    fill_circle(x2, y2, w / 2.0, c)


def stroke_poly(pts, w, c, close=False):
    for i in range(len(pts) - 1):
        stroke_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], w, c)
    if close and len(pts) > 2:
        stroke_line(pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], w, c)


def stroke_circle(cx, cy, r, w, c):
    pts = []
    for i in range(40):
        a = 2.0 * math.pi * i / 40.0
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    stroke_poly(pts, w, c, close=True)


def stroke_arc(cx, cy, r, a0, a1, w, c):
    pts = []
    steps = max(6, int(abs(a1 - a0) / 9.0))
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    stroke_poly(pts, w, c)


def stroke_rect(x, y, w, h, lw, c):
    stroke_poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], lw, c,
                close=True)


# ---------------------------------------------------------------- font
# Stroke typeface. Each glyph is a list of polylines on a grid where
# x runs 0..7 and y runs 0 (baseline) .. 10 (cap height); lower case
# sits 0..7, descenders go negative. A stroke ending in 'Z' is closed.
_FONT_RAW = {
    'A': "0,0 3.5,10 7,0;1.7,3.8 5.3,3.8",
    'B': "0,0 0,10;0,10 3.8,10 5.2,8.6 5.2,6.4 3.8,5.2 0,5.2;"
         "0,5.2 4.2,5.2 5.8,3.8 5.8,1.4 4.2,0 0,0",
    'C': "6.5,8.5 4.5,10 2,10 0.5,7.5 0.5,2.5 2,0 4.5,0 6.5,1.5",
    'D': "0,0 0,10;0,10 4,10 6,7.5 6,2.5 4,0 0,0",
    'E': "6,10 0,10 0,0 6,0;0,5.2 4.5,5.2",
    'F': "6,10 0,10 0,0;0,5.2 4.2,5.2",
    'G': "6.5,8.5 4.5,10 2,10 0.5,7.5 0.5,2.5 2,0 4.8,0 6.5,1.8 6.5,4.2 "
         "4.2,4.2",
    'H': "0,0 0,10;7,0 7,10;0,5 7,5",
    'I': "3.5,0 3.5,10;1.3,10 5.7,10;1.3,0 5.7,0",
    'J': "6.5,10 6.5,2 5,0 2.5,0 1,1.5",
    'K': "0,0 0,10;6.5,10 0.8,4.2;1.6,5 6.5,0",
    'L': "0,10 0,0 6,0",
    'M': "0,0 0,10 3.5,3 7,10 7,0",
    'N': "0,0 0,10 7,0 7,10",
    'O': "2,0 0.5,2.5 0.5,7.5 2,10 5,10 6.5,7.5 6.5,2.5 5,0 2,0 Z",
    'P': "0,0 0,10;0,10 4.5,10 6,8.6 6,6.2 4.5,5 0,5",
    'Q': "2,0 0.5,2.5 0.5,7.5 2,10 5,10 6.5,7.5 6.5,2.5 5,0 2,0 Z;"
         "4.2,2.8 7.2,-0.6",
    'R': "0,0 0,10;0,10 4.5,10 6,8.6 6,6.2 4.5,5 0,5;3.8,5 6.5,0",
    'S': "6.3,8.6 4.5,10 2,10 0.7,8.4 0.7,6.6 2,5.2 5,3.8 6.3,2.4 6.3,1.2 "
         "4.8,0 2,0 0.7,1.4",
    'T': "3.5,0 3.5,10;0,10 7,10",
    'U': "0,10 0,2.5 2,0 5,0 7,2.5 7,10",
    'V': "0,10 3.5,0 7,10",
    'W': "0,10 1.8,0 3.5,7 5.2,0 7,10",
    'X': "0,0 7,10;0,10 7,0",
    'Y': "0,10 3.5,5.5 7,10;3.5,5.5 3.5,0",
    'Z': "0,10 7,10 0,0 7,0",
    'a': "6.5,7 6.5,0;5,7 2,7 0.5,5.2 0.5,1.8 2,0 5,0 6.5,1.8",
    'b': "0,10 0,0;0,2 2,0 5,0 6.5,2 6.5,5 5,7 2,7 0,5",
    'c': "6.3,5.6 4.8,7 2.2,7 0.6,5.2 0.6,1.8 2.2,0 4.8,0 6.3,1.4",
    'd': "6.5,10 6.5,0;6.5,2 5,0 2,0 0.5,2 0.5,5 2,7 5,7 6.5,5",
    'e': "0.5,3.5 6.3,3.5 6.3,5.2 5,7 2.2,7 0.5,5.2 0.5,1.8 2.2,0 5,0 "
         "6.3,1.2",
    'f': "2.2,0 2.2,8.4 3.2,9.8 5.2,10;0.7,6.8 4.8,6.8",
    'g': "6.5,7 6.5,-2.2 5.2,-3.4 2.2,-3.4 0.9,-2.2;"
         "5,7 2,7 0.5,5.2 0.5,1.8 2,0 5,0 6.5,1.8",
    'h': "0,10 0,0;0,5 2,7 5,7 6.5,5 6.5,0",
    'i': "3,7 3,0;3,9.1 3,9.5",
    'j': "3.2,7 3.2,-2.2 2,-3.4 0.6,-2.6;3.2,9.1 3.2,9.5",
    'k': "0,10 0,0;6.2,7 1,2.8;1.8,3.6 6.5,0",
    'l': "3,10 3,0",
    'm': "0,7 0,0;0,4.8 1.7,7 3.2,4.8 3.2,0;3.2,4.8 4.7,7 6.4,4.8 "
         "6.4,0",
    'n': "0,7 0,0;0,4.8 1.8,7 5,7 6.5,4.8 6.5,0",
    'o': "2,0 0.5,1.8 0.5,5.2 2,7 5,7 6.5,5.2 6.5,1.8 5,0 2,0 Z",
    'p': "0,-3.2 0,7;0,2 2,0 5,0 6.5,2 6.5,5 5,7 2,7 0,5",
    'q': "6.5,-3.2 6.5,7;6.5,2 5,0 2,0 0.5,2 0.5,5 2,7 5,7 6.5,5",
    'r': "0,7 0,0;0,4.4 1.8,6.8 4.8,7",
    's': "6.2,5.8 4.6,7 2,7 0.7,5.9 0.7,4.6 2,3.4 5,2.4 6.3,1.4 6.3,0.6 "
         "4.8,0 2,0 0.7,0.9",
    't': "3,10 3,1.4 4.2,0 5.8,0;0.9,7 5.4,7",
    'u': "0,7 0,1.8 2,0 4.8,0 6.5,1.8 6.5,7;6.5,0 6.5,1.2",
    'v': "0,7 3.2,0 6.5,7",
    'w': "0,7 1.6,0 3.2,5 4.8,0 6.5,7",
    'x': "0,0 6.5,7;0,7 6.5,0",
    'y': "0,7 3.2,0.8 6.5,7;3.2,0.8 3.2,-3.2",
    'z': "0,7 6.5,7 0,0 6.5,0",
    '0': "2.2,0 0.7,1.5 0.7,8.5 2.2,10 4.8,10 6.3,8.5 6.3,1.5 4.8,0 "
         "2.2,0 Z",
    '1': "1.2,7.8 4.2,10 4.2,0;1.2,0 6.8,0",
    '2': "0.8,8.4 2.2,10 4.8,10 6.2,8.4 6.2,6.4 0.8,0 6.5,0",
    '3': "0.8,8.6 2.4,10 4.6,10 6,8.6 6,6.8 4.6,5.4 2.6,5.4;"
         "2.6,5.4 4.8,5.4 6.3,3.8 6.3,1.4 4.8,0 2.2,0 0.8,1.4",
    '4': "5,0 5,10 0.6,2.6 7,2.6",
    '5': "6.3,10 1,10 0.8,5.8;0.8,5.8 2.8,6.8 5,6.6 6.4,5 6.4,1.6 5,0 "
         "2.2,0 0.8,1.3",
    '6': "2.2,5 0.8,3.6 0.8,1.4 2.2,0 4.8,0 6.2,1.4 6.2,3.6 4.8,5 "
         "2.2,5 Z;5.6,9.6 3.4,10 1.6,8.2 0.8,5.4 0.8,3.6",
    '7': "0.7,10 6.8,10 3.4,0",
    '8': "2.4,5.2 1,6.6 1,8.6 2.4,10 4.6,10 6,8.6 6,6.6 4.6,5.2 2.4,5.2 "
         "1,3.6 1,1.4 2.4,0 4.6,0 6,1.4 6,3.6 4.6,5.2",
    '9': "2.2,5 0.8,6.4 0.8,8.6 2.2,10 4.8,10 6.2,8.6 6.2,6.4 4.8,5 "
         "2.2,5 Z;6.2,8.6 6.2,2.6 5.2,0.6 3.2,0",
    '.': "3,0 3,0.5",
    ',': "3.4,1.4 2.7,-1.8",
    '-': "0.8,4.5 5.8,4.5",
    '+': "3.3,1.5 3.3,8.5;0.5,5 6,5",
    '$': "6.3,8.6 4.5,10 2,10 0.7,8.4 0.7,6.6 2,5.2 5,3.8 6.3,2.4 6.3,1.2 "
         "4.8,0 2,0 0.7,1.4;3.5,-1.2 3.5,11.2",
    '%': "3.6,7.6 3.1,8.8 1.9,9.3 0.7,8.8 0.2,7.6 0.7,6.4 1.9,5.9 3.1,6.4 "
         "3.6,7.6 Z;6,0.5 1,9.5;"
         "6.8,2.4 6.3,3.6 5.1,4.1 3.9,3.6 3.4,2.4 3.9,1.2 5.1,0.7 6.3,1.2 "
         "6.8,2.4 Z",
    '/': "1,0 6,10",
    '(': "5.2,10 2.8,6.5 2.8,3.5 5.2,0",
    ')': "1.8,10 4.2,6.5 4.2,3.5 1.8,0",
    ':': "3,1.6 3,2.1;3,7.9 3,8.4",
    ';': "3,7.9 3,8.4;3.4,1.4 2.7,-1.8",
    '!': "3.3,10 3.3,3.4;3.3,0 3.3,0.5",
    '?': "0.8,8.4 2.4,10 4.8,10 6.2,8.4 6.2,6.6 3.4,4.2 3.4,2.8;"
         "3.4,0 3.4,0.5",
    "'": "3,10 2.6,7.6",
    '"': "1.8,10 1.4,7.6;5,10 4.6,7.6",
    '&': "6.3,0.8 1.8,5.6 1.2,7.6 2.2,9.8 4,9.6 4.6,7.8 1,3.2 0.8,1.2 "
         "2.4,0 4.4,0.6 6.3,3.4",
    '~': "0.5,5 2,6.6 4,3.4 6,5",
    '=': "0.8,6.8 6,6.8;0.8,3.2 6,3.2",
    '|': "3.3,0 3.3,10",
    '<': "6,10 0.8,5 6,0",
    '>': "0.8,10 6,5 0.8,0",
}


def _parse_font(raw):
    font = {}
    for ch, spec in raw.items():
        strokes = []
        for part in spec.split(';'):
            part = part.strip()
            closed = part.endswith('Z')
            if closed:
                part = part[:-1].strip()
            pts = []
            for pair in part.split():
                a, b = pair.split(',')
                pts.append((float(a), float(b)))
            strokes.append((pts, closed))
        font[ch] = strokes
    return font


GLYPHS = _parse_font(_FONT_RAW)

_ADV = {
    ' ': 4.6, 'i': 3.8, 'j': 4.4, 'l': 3.8, 't': 5.6, 'f': 5.2,
    'r': 5.6, 'm': 11.2, 'w': 10.8, 'M': 11.2, 'W': 11.4, 'I': 6.4,
    '.': 4.0, ',': 4.0, ':': 4.0, ';': 4.0, '!': 4.0, "'": 3.6,
    '"': 6.4, '-': 6.2, '|': 4.0, '(': 5.4, ')': 5.4, '1': 7.8,
}


def _adv(ch):
    return _ADV.get(ch, 8.6)


def text_w(s, size):
    return sum(_adv(c) for c in s) * size / 10.0


def draw_text(x, y, s, size, color, weight, align='l', serif=False,
              italic=False):
    """Draw one line of stroke type. (x, y) is the baseline start."""
    w = text_w(s, size)
    if align == 'c':
        x -= w / 2.0
    elif align == 'r':
        x -= w
    unit = size / 10.0
    shear = 0.17 if italic else 0.0
    pen = x
    for ch in s:
        if ch == ' ':
            pen += _adv(ch) * unit
            continue
        if ch == '·':
            fill_circle(pen + 2.0 * unit, y - 3.0 * unit, weight * 0.55,
                        color)
            pen += _adv(ch) * unit if ch in _ADV else 4.0 * unit
            continue
        glyph = GLYPHS.get(ch)
        if glyph is None:
            glyph = GLYPHS.get(ch.upper())
        if glyph is None:
            pen += _adv(ch) * unit
            continue
        for pts, closed in glyph:
            P = [(pen + (px + shear * py) * unit, y - py * unit)
                 for px, py in pts]
            stroke_poly(P, weight, color, close=closed)
            if serif:
                for idx in (0, -1):
                    px, py = pts[idx]
                    if py not in (0.0, 10.0):
                        continue
                    nb = pts[1] if idx == 0 else pts[-2]
                    if abs(nb[0] - px) > 1.6:
                        continue
                    X = pen + (px + shear * py) * unit
                    Y = y - py * unit
                    stroke_line(X - 1.15 * unit, Y, X + 1.15 * unit, Y,
                                weight * 0.72, color)
        pen += _adv(ch) * unit
    return pen


def wrap(s, size, maxw):
    words = s.split()
    lines = []
    cur = ''
    for wd in words:
        t = (cur + ' ' + wd) if cur else wd
        if text_w(t, size) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_para(x, ytop, s, size, color, weight, maxw, lh, align='l',
              italic=False, max_lines=None):
    """Wrapped paragraph; ytop is the top of the first line's cap."""
    lines = wrap(s, size, maxw)
    if max_lines is not None:
        lines = lines[:max_lines]
    y = ytop + size
    for ln in lines:
        draw_text(x, y, ln, size, color, weight, align=align,
                  italic=italic)
        y += lh
    return ytop + len(lines) * lh


# ---------------------------------------------------------------- art
# Every panel's illustration is flat vector geometry matched to its
# story. Each function paints inside the box (x, y, w, h).

def _flag_us(x, y, w, h):
    fill_rect(x, y, w, h, (250, 248, 244))
    for i in range(3):
        fill_rect(x, y + i * 2 * h / 7.0, w, h / 7.0, RED)
    fill_rect(x, y, w * 0.45, h * 4 / 7.0, BLUE)
    stroke_rect(x, y, w, h, 0.8, INK)


def _flag_cn(x, y, w, h):
    fill_rect(x, y, w, h, RED)
    fill_circle(x + w * 0.24, y + h * 0.3, h * 0.13, GOLD)
    for dx, dy in ((0.62, 0.16), (0.72, 0.36), (0.72, 0.58), (0.6, 0.76)):
        fill_circle(x + w * dx, y + h * dy, h * 0.07, GOLD)
    stroke_rect(x, y, w, h, 0.8, INK)


def _flag_ru(x, y, w, h):
    fill_rect(x, y, w, h / 3.0, (250, 248, 244))
    fill_rect(x, y + h / 3.0, w, h / 3.0, BLUE)
    fill_rect(x, y + 2 * h / 3.0, w, h / 3.0, RED)
    stroke_rect(x, y, w, h, 0.8, INK)


def _flag_eu(x, y, w, h):
    fill_rect(x, y, w, h, BLUE)
    for i in range(6):
        a = 2.0 * math.pi * i / 6.0
        fill_circle(x + w / 2 + w * 0.3 * math.cos(a),
                    y + h / 2 + h * 0.3 * math.sin(a), h * 0.07, GOLD)
    stroke_rect(x, y, w, h, 0.8, INK)


def art_summit(x, y, w, h):
    fill_rect(x, y, w, h, SKY)
    # three leaders: heads and shoulders behind a long table
    cx = [x + w * 0.26, x + w * 0.5, x + w * 0.74]
    skin = [(232, 190, 160), (240, 205, 170), (226, 182, 150)]
    suit = [BLUE, (60, 60, 66), (90, 44, 44)]
    for i in range(3):
        fill_poly([(cx[i] - w * 0.11, y + h * 0.78), (cx[i] - w * 0.09,
                  y + h * 0.52), (cx[i] + w * 0.09, y + h * 0.52),
                   (cx[i] + w * 0.11, y + h * 0.78)], suit[i])
        fill_circle(cx[i], y + h * 0.42, h * 0.13, skin[i])
        fill_poly([(cx[i] - h * 0.13, y + h * 0.40), (cx[i] - h * 0.12,
                    y + h * 0.30), (cx[i] + h * 0.12, y + h * 0.30),
                   (cx[i] + h * 0.13, y + h * 0.40),
                   (cx[i], y + h * 0.34)], (70, 62, 55))
    # table
    fill_poly([(x + w * 0.06, y + h * 0.98), (x + w * 0.13, y + h * 0.74),
               (x + w * 0.87, y + h * 0.74), (x + w * 0.94, y + h * 0.98)],
              BROWN)
    fill_rect(x + w * 0.13, y + h * 0.74, w * 0.74, h * 0.045, (150, 108, 70))
    # signed document on the table
    dx, dy = x + w * 0.44, y + h * 0.80
    fill_rect(dx, dy, w * 0.13, h * 0.13, (253, 250, 243))
    for i in range(3):
        fill_rect(dx + w * 0.015, dy + h * 0.025 + i * h * 0.032,
                  w * 0.10, h * 0.012, GREY)
    # three flags on poles behind
    fw, fh = w * 0.15, h * 0.30
    for i, fn in enumerate((_flag_us, _flag_cn, _flag_ru)):
        fx = x + w * (0.10 + 0.33 * i)
        stroke_line(fx, y + h * 0.52, fx, y + h * 0.06, 1.6, INK)
        fn(fx + 2, y + h * 0.06, fw, fh)


def art_court(x, y, w, h):
    fill_rect(x, y, w, h, (228, 222, 205))
    bx, bw = x + w * 0.08, w * 0.52
    # pediment, entablature, columns, steps
    fill_poly([(bx - w * 0.03, y + h * 0.30), (bx + bw / 2, y + h * 0.06),
               (bx + bw + w * 0.03, y + h * 0.30)], (168, 158, 138))
    fill_rect(bx - w * 0.02, y + h * 0.30, bw + w * 0.04, h * 0.07,
              (178, 168, 148))
    for i in range(4):
        cx = bx + bw * (0.08 + 0.24 * i)
        fill_rect(cx, y + h * 0.37, bw * 0.11, h * 0.44, (238, 232, 216))
        fill_rect(cx - bw * 0.015, y + h * 0.37, bw * 0.14, h * 0.045,
                  (178, 168, 148))
        fill_rect(cx - bw * 0.015, y + h * 0.765, bw * 0.14, h * 0.045,
                  (178, 168, 148))
    fill_rect(bx - w * 0.03, y + h * 0.81, bw + w * 0.06, h * 0.055,
              (178, 168, 148))
    fill_rect(bx - w * 0.05, y + h * 0.865, bw + w * 0.10, h * 0.055,
              (168, 158, 138))
    # scales of justice on the right
    sx, sy = x + w * 0.80, y + h * 0.16
    stroke_line(sx, sy, sx, sy + h * 0.62, 2.2, GOLD)
    stroke_line(sx - w * 0.13, sy + h * 0.08, sx + w * 0.13, sy + h * 0.08,
                2.2, GOLD)
    fill_circle(sx, sy, h * 0.045, GOLD)
    for sgn in (-1, 1):
        px = sx + sgn * w * 0.13
        stroke_line(px, sy + h * 0.08, px - w * 0.05, sy + h * 0.34, 1.3,
                    GOLD)
        stroke_line(px, sy + h * 0.08, px + w * 0.05, sy + h * 0.34, 1.3,
                    GOLD)
        fill_poly([(px - w * 0.055, sy + h * 0.34), (px + w * 0.055,
                    sy + h * 0.34), (px, sy + h * 0.44)], GOLD)
    fill_rect(sx - w * 0.07, sy + h * 0.78, w * 0.14, h * 0.05, GOLD)


def art_chart_fall(x, y, w, h):
    fill_rect(x, y, w, h, (250, 244, 238))
    for i in range(1, 4):
        fill_rect(x + w * 0.06, y + h * i / 4.0, w * 0.9, 0.7,
                  (224, 214, 200))
    # candlesticks sliding down
    tops = [0.16, 0.24, 0.20, 0.34, 0.44, 0.40, 0.56, 0.68]
    for i, t in enumerate(tops):
        cx = x + w * (0.10 + 0.105 * i)
        cy = y + h * t
        col = RED if i % 3 != 2 else GREEN
        fill_rect(cx - w * 0.028, cy, w * 0.056, h * 0.17, col)
        stroke_line(cx, cy - h * 0.06, cx, cy + h * 0.23, 1.4, col)
    # the falling line and arrow
    pts = [(x + w * (0.08 + 0.115 * i), y + h * (t + 0.05))
           for i, t in enumerate(tops)]
    stroke_poly(pts, 3.0, RED)
    lx, ly = pts[-1]
    fill_poly([(lx + w * 0.10, ly + h * 0.16), (lx + w * 0.015, ly + h * 0.15),
               (lx + w * 0.075, ly + h * 0.045)], RED)


def art_anthropic(x, y, w, h):
    fill_rect(x, y, w, h, (240, 246, 238))
    for i in range(1, 4):
        fill_rect(x + w * 0.05, y + h * i / 4.0, w * 0.62, 0.7,
                  (214, 224, 208))
    pts = [(x + w * 0.07, y + h * 0.80), (x + w * 0.20, y + h * 0.66),
           (x + w * 0.32, y + h * 0.72), (x + w * 0.45, y + h * 0.48),
           (x + w * 0.58, y + h * 0.34)]
    stroke_poly(pts, 2.6, GREEN)
    lx, ly = pts[-1]
    fill_poly([(lx + w * 0.085, ly - h * 0.13), (lx + w * 0.005, ly - h * 0.02),
               (lx - w * 0.055, ly + h * 0.075)], GREEN)
    # the opening bell
    bx, by = x + w * 0.80, y + h * 0.16
    bell = [(bx - w * 0.085, by + h * 0.34), (bx - w * 0.07, by + h * 0.12),
            (bx - w * 0.03, by + h * 0.03), (bx + w * 0.03, by + h * 0.03),
            (bx + w * 0.07, by + h * 0.12), (bx + w * 0.085, by + h * 0.34)]
    fill_poly(bell, GOLD)
    fill_rect(bx - w * 0.095, by + h * 0.34, w * 0.19, h * 0.045, GOLD)
    fill_circle(bx, by + h * 0.46, h * 0.05, GOLD)
    fill_circle(bx, by - h * 0.015, h * 0.035, BROWN)
    for sgn in (-1, 1):
        stroke_arc(bx, by + h * 0.18, w * (0.13 + 0.0), -60, 60, 1.2, GOLD) \
            if sgn > 0 else stroke_arc(bx, by + h * 0.18, w * 0.13, 120, 240,
                                       1.2, GOLD)


def art_berlin(x, y, w, h):
    fill_rect(x, y, w, h, SKY)
    cx, cy = x + w / 2, y + h * 0.54
    flags = [_flag_eu, _flag_us, _flag_cn, _flag_ru, _flag_eu, _flag_us,
             _flag_cn, _flag_ru]
    cols = [BLUE, RED, GOLD, TEAL, GREEN, BROWN, BLUE, RED]
    for i in range(8):
        a = 2.0 * math.pi * i / 8.0
        fx = cx + w * 0.40 * math.cos(a)
        fy = cy + h * 0.36 * math.sin(a)
        stroke_line(fx, fy + h * 0.15, fx, fy - h * 0.13, 1.3, INK)
        fill_rect(fx + 1.5, fy - h * 0.13, w * 0.085, h * 0.15, cols[i])
    # the loan document at the centre
    dx, dy, dw, dh = cx - w * 0.11, cy - h * 0.24, w * 0.22, h * 0.48
    fill_rect(dx, dy, dw, dh, (253, 250, 243))
    stroke_rect(dx, dy, dw, dh, 1.2, INK)
    stroke_arc(dx + dw * 0.34, dy + dh * 0.34, dw * 0.17, 100, 440, 2.4, BLUE)
    stroke_line(dx + dw * 0.18, dy + dh * 0.34, dx + dw * 0.52,
                dy + dh * 0.34, 2.4, BLUE)
    stroke_line(dx + dw * 0.18, dy + dh * 0.46, dx + dw * 0.52,
                dy + dh * 0.46, 2.4, BLUE)
    for i in range(2):
        fill_rect(dx + dw * 0.16, dy + dh * (0.62 + 0.15 * i), dw * 0.68,
                  dh * 0.05, GREY)


def art_gulf(x, y, w, h):
    fill_rect(x, y, w, h, SKY)
    # coastline
    fill_poly([(x, y), (x + w * 0.52, y), (x + w * 0.44, y + h * 0.30),
               (x + w * 0.55, y + h * 0.52), (x + w * 0.30, y + h * 0.62),
               (x, y + h * 0.58)], SAND)
    # sea
    fill_poly([(x, y + h * 0.58), (x + w * 0.30, y + h * 0.62),
               (x + w * 0.55, y + h * 0.52), (x + w, y + h * 0.44),
               (x + w, y + h), (x, y + h)], SEA)
    for i in range(3):
        stroke_arc(x + w * (0.58 + 0.14 * i), y + h * (0.78 + 0.05 * (i % 2)),
                   w * 0.045, 180, 360, 1.3, (220, 234, 244))
    # drone
    dx, dy = x + w * 0.66, y + h * 0.26
    fill_rect(dx - w * 0.05, dy - h * 0.05, w * 0.10, h * 0.10, (44, 46, 52))
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        ex, ey = dx + sx * w * 0.115, dy + sy * h * 0.16
        stroke_line(dx, dy, ex, ey, 1.8, (44, 46, 52))
        stroke_circle(ex, ey, w * 0.032, 1.6, (44, 46, 52))
    stroke_line(dx, dy + h * 0.05, dx + w * 0.03, dy + h * 0.30, 1.2,
                (120, 130, 140))
    # tanker below right
    tx, ty = x + w * 0.60, y + h * 0.74
    fill_poly([(tx, ty), (tx + w * 0.34, ty), (tx + w * 0.30, ty + h * 0.10),
               (tx + w * 0.04, ty + h * 0.10)], (52, 54, 60))
    fill_rect(tx + w * 0.05, ty - h * 0.055, w * 0.22, h * 0.055, RED)
    fill_rect(tx + w * 0.27, ty - h * 0.10, w * 0.045, h * 0.10,
              (52, 54, 60))
    # strike burst on the hull
    bx, by = tx + w * 0.17, ty + h * 0.03
    for i in range(6):
        a = 2.0 * math.pi * i / 6.0
        stroke_line(bx, by, bx + w * 0.045 * math.cos(a),
                    by + h * 0.09 * math.sin(a), 1.8, GOLD)


def art_cop(x, y, w, h):
    fill_rect(x, y, w, h, (238, 244, 238))
    gx, gy, gr = x + w * 0.30, y + h * 0.52, h * 0.36
    fill_circle(gx, gy, gr, SEA)
    fill_poly([(gx - gr * 0.7, gy - gr * 0.5), (gx - gr * 0.2, gy - gr * 0.75),
               (gx + gr * 0.1, gy - gr * 0.45), (gx - gr * 0.25, gy - gr * 0.1),
               (gx - gr * 0.65, gy - gr * 0.15)], GREEN)
    fill_poly([(gx + gr * 0.15, gy + gr * 0.25), (gx + gr * 0.6, gy + gr * 0.1),
               (gx + gr * 0.72, gy + gr * 0.5), (gx + gr * 0.3, gy + gr * 0.72),
               (gx + gr * 0.05, gy + gr * 0.5)], GREEN)
    stroke_circle(gx, gy, gr, 1.4, BLUE)
    stroke_arc(gx, gy, gr * 0.55, 90, 270, 1.1, BLUE)
    stroke_arc(gx, gy, gr * 0.55, 270, 450, 1.1, BLUE)
    stroke_line(gx - gr, gy, gx + gr, gy, 1.1, BLUE)
    # draft document with the fossil line struck through
    dx, dy, dw, dh = x + w * 0.58, y + h * 0.14, w * 0.36, h * 0.72
    fill_rect(dx, dy, dw, dh, (253, 250, 243))
    stroke_rect(dx, dy, dw, dh, 1.2, INK)
    # oil drop at the top of the page
    ox, oy = dx + dw * 0.5, dy + dh * 0.16
    fill_poly([(ox, oy - dh * 0.10), (ox + dw * 0.13, oy + dh * 0.06),
               (ox + dw * 0.10, oy + dh * 0.13), (ox, oy + dh * 0.16),
               (ox - dw * 0.10, oy + dh * 0.13),
               (ox - dw * 0.13, oy + dh * 0.06)], INK)
    for i in range(3):
        fill_rect(dx + dw * 0.14, dy + dh * (0.42 + 0.14 * i), dw * 0.72,
                  dh * 0.045, GREY)
    stroke_line(dx + dw * 0.08, dy + dh * 0.52, dx + dw * 0.92,
                dy + dh * 0.30, 2.6, RED)


def art_ebola(x, y, w, h):
    fill_rect(x, y, w, h, (246, 238, 240))
    cx, cy, r = x + w * 0.40, y + h * 0.52, h * 0.26
    for i in range(9):
        a = 2.0 * math.pi * i / 9.0
        ex, ey = cx + (r + h * 0.10) * math.cos(a), cy + (r + h * 0.10) * \
            math.sin(a)
        stroke_line(cx + r * 0.8 * math.cos(a), cy + r * 0.8 * math.sin(a),
                    ex, ey, 2.0, (150, 70, 96))
        fill_circle(ex, ey, h * 0.05, (150, 70, 96))
    fill_circle(cx, cy, r, (172, 92, 116))
    fill_circle(cx - r * 0.3, cy - r * 0.25, r * 0.22, (196, 130, 152))
    fill_circle(cx + r * 0.32, cy + r * 0.3, r * 0.16, (196, 130, 152))
    # medical cross badge
    bx, by = x + w * 0.78, y + h * 0.30
    fill_circle(bx, by, h * 0.17, (253, 250, 243))
    stroke_circle(bx, by, h * 0.17, 1.4, RED)
    fill_rect(bx - h * 0.035, by - h * 0.10, h * 0.07, h * 0.20, RED)
    fill_rect(bx - h * 0.10, by - h * 0.035, h * 0.20, h * 0.07, RED)


def art_florida(x, y, w, h):
    fill_rect(x, y, w, h, (226, 233, 238))
    # storm cloud
    cy = y + h * 0.26
    for dx, r in ((-0.24, 0.15), (-0.08, 0.20), (0.10, 0.17), (0.24, 0.12)):
        fill_circle(x + w * (0.5 + dx), cy, h * r, (120, 132, 148))
    fill_rect(x + w * 0.26, cy, w * 0.48, h * 0.10, (120, 132, 148))
    # rain
    for i in range(7):
        rx = x + w * (0.30 + 0.065 * i)
        stroke_line(rx, y + h * 0.44, rx - w * 0.02, y + h * 0.60, 1.5,
                    (84, 118, 158))
    # rooftops poking out of the flood
    for i, (hx, hw) in enumerate(((0.10, 0.24), (0.42, 0.26), (0.72, 0.22))):
        gx = x + w * hx
        gw = w * hw
        fill_rect(gx, y + h * 0.68, gw, h * 0.20, (238, 232, 216))
        fill_poly([(gx - gw * 0.06, y + h * 0.68), (gx + gw * 0.5,
                    y + h * 0.52), (gx + gw * 1.06, y + h * 0.68)], RED
                  if i == 1 else BROWN)
    # flood water
    fill_rect(x, y + h * 0.80, w, h * 0.20, SEA)
    for i in range(4):
        stroke_arc(x + w * (0.14 + 0.22 * i), y + h * 0.90, w * 0.05, 180,
                   360, 1.4, (220, 234, 244))


def art_chip(x, y, w, h):
    fill_rect(x, y, w, h, (238, 240, 244))
    cw, chh = w * 0.44, h * 0.58
    cx, cy = x + (w - cw) / 2, y + (h - chh) / 2
    for i in range(4):
        t = (i + 0.5) / 4.0
        fill_rect(cx - w * 0.07, cy + chh * t - h * 0.02, w * 0.07, h * 0.04,
                  GREY)
        fill_rect(cx + cw, cy + chh * t - h * 0.02, w * 0.07, h * 0.04, GREY)
        fill_rect(cx + cw * t - w * 0.02, cy - h * 0.07, w * 0.04, h * 0.07,
                  GREY)
        fill_rect(cx + cw * t - w * 0.02, cy + chh, w * 0.04, h * 0.07, GREY)
    fill_rect(cx, cy, cw, chh, (52, 58, 70))
    fill_rect(cx + cw * 0.22, cy + chh * 0.22, cw * 0.56, chh * 0.56,
              (96, 106, 124))
    fill_circle(cx + cw * 0.5, cy + chh * 0.5, h * 0.045, (200, 208, 220))
    # barrier stamp: no-entry sign over the corner
    bx, by, br = x + w * 0.80, y + h * 0.26, h * 0.19
    fill_circle(bx, by, br, (253, 250, 243))
    stroke_circle(bx, by, br, 2.6, RED)
    stroke_line(bx - br * 0.68, by + br * 0.68, bx + br * 0.68,
                by - br * 0.68, 2.6, RED)


def art_gta(x, y, w, h):
    fill_rect(x, y, w, h, (250, 214, 170))
    fill_circle(x + w * 0.78, y + h * 0.34, h * 0.17, (244, 150, 60))
    # skyline silhouette
    for bx, bw, bh in ((0.02, 0.10, 0.42), (0.14, 0.08, 0.58),
                       (0.24, 0.11, 0.36), (0.55, 0.09, 0.52),
                       (0.66, 0.12, 0.40), (0.80, 0.08, 0.60),
                       (0.90, 0.09, 0.44)):
        fill_rect(x + w * bx, y + h * (0.72 - bh * 0.55), w * bw,
                  h * bh * 0.55, (92, 62, 84))
    fill_rect(x, y + h * 0.72, w, h * 0.28, (70, 48, 66))
    # palm tree
    px, py = x + w * 0.44, y + h * 0.72
    stroke_poly([(px - w * 0.02, py), (px, py - h * 0.30),
                 (px + w * 0.03, py - h * 0.44)], 2.6, (60, 44, 40))
    for a in (200, 245, 290, 335):
        stroke_arc(px + w * 0.03, py - h * 0.44, w * 0.085, a, a + 55, 2.2,
                   GREEN)
    # game controller, front and centre
    gx, gy, gw, gh = x + w * 0.30, y + h * 0.60, w * 0.40, h * 0.30
    fill_ellipse(gx + gw / 2, gy + gh / 2, gw / 2, gh / 2, (30, 28, 36))
    fill_rect(gx + gw * 0.14, gy + gh * 0.40, gw * 0.20, gh * 0.16,
              (230, 228, 220))
    fill_rect(gx + gw * 0.205, gy + gh * 0.30, gw * 0.07, gh * 0.36,
              (230, 228, 220))
    fill_circle(gx + gw * 0.76, gy + gh * 0.38, gh * 0.11, RED)
    fill_circle(gx + gw * 0.87, gy + gh * 0.52, gh * 0.11, GOLD)
    fill_circle(gx + gw * 0.65, gy + gh * 0.55, gh * 0.09, TEAL)


def art_voyager(x, y, w, h):
    fill_rect(x, y, w, h, NAVY)
    # stars
    for sx, sy in ((0.08, 0.18), (0.2, 0.62), (0.36, 0.12), (0.55, 0.2),
                   (0.7, 0.1), (0.86, 0.3), (0.62, 0.62), (0.9, 0.66),
                   (0.14, 0.36), (0.44, 0.82)):
        fill_circle(x + w * sx, y + h * sy, 1.1, (240, 240, 230))
    # the probe: big dish, bus, long boom
    dx, dy = x + w * 0.34, y + h * 0.52
    fill_poly([(dx - w * 0.20, dy - h * 0.30), (dx + w * 0.02, dy),
               (dx - w * 0.20, dy + h * 0.30), (dx - w * 0.13, dy)],
              (238, 236, 228))
    fill_circle(dx - w * 0.155, dy, h * 0.045, GOLD)
    fill_rect(dx + w * 0.02, dy - h * 0.09, w * 0.13, h * 0.18, GOLD)
    stroke_line(dx + w * 0.15, dy + h * 0.06, dx + w * 0.40, dy + h * 0.30,
                1.8, (200, 200, 190))
    fill_rect(dx + w * 0.385, dy + h * 0.27, w * 0.035, h * 0.09,
              (200, 200, 190))
    stroke_line(dx + w * 0.08, dy - h * 0.09, dx + w * 0.20, dy - h * 0.30,
                1.5, (200, 200, 190))
    # signal arcs travelling home (down-left, toward a small Earth)
    for r in (0.16, 0.26, 0.36):
        stroke_arc(dx - w * 0.10, dy + h * 0.10, w * r, 120, 205, 1.8,
                   (140, 190, 235))
    ex, ey = x + w * 0.10, y + h * 0.84
    fill_circle(ex, ey, h * 0.075, SEA)
    fill_poly([(ex - h * 0.04, ey - h * 0.03), (ex + h * 0.01, ey - h * 0.05),
               (ex + h * 0.045, ey), (ex, ey + h * 0.045),
               (ex - h * 0.045, ey + 0.0)], GREEN)


def art_tennis(x, y, w, h):
    fill_rect(x, y, w, h, (86, 128, 92))
    fill_rect(x + w * 0.08, y + h * 0.14, w * 0.84, h * 0.72, (70, 104, 150))
    stroke_rect(x + w * 0.08, y + h * 0.14, w * 0.84, h * 0.72, 1.5,
                (250, 250, 246))
    stroke_line(x + w * 0.08, y + h * 0.50, x + w * 0.92, y + h * 0.50, 1.5,
                (250, 250, 246))
    stroke_line(x + w * 0.50, y + h * 0.14, x + w * 0.50, y + h * 0.86, 1.0,
                (250, 250, 246))
    fill_rect(x + w * 0.08, y + h * 0.475, w * 0.84, h * 0.05, (40, 40, 44))
    # player figure, mid-swing
    px, py = x + w * 0.30, y + h * 0.34
    fill_circle(px, py, h * 0.075, (240, 205, 170))
    stroke_line(px, py + h * 0.07, px - w * 0.01, py + h * 0.30, 2.6, INK)
    stroke_line(px - w * 0.01, py + h * 0.30, px - w * 0.09, py + h * 0.52,
                2.6, INK)
    stroke_line(px - w * 0.01, py + h * 0.30, px + w * 0.09, py + h * 0.50,
                2.6, INK)
    stroke_line(px, py + h * 0.12, px + w * 0.13, py - h * 0.02, 2.6, INK)
    # racket in the raised hand
    rx, ry = px + w * 0.185, py - h * 0.10
    stroke_line(px + w * 0.13, py - h * 0.02, rx - w * 0.02, ry + h * 0.08,
                2.2, BROWN)
    pts = []
    for i in range(24):
        a = 2.0 * math.pi * i / 24.0
        pts.append((rx + w * 0.055 * math.cos(a), ry + h * 0.13 *
                    math.sin(a)))
    stroke_poly(pts, 2.0, BROWN, close=True)
    stroke_line(rx - w * 0.045, ry, rx + w * 0.045, ry, 0.9, GREY)
    stroke_line(rx, ry - h * 0.11, rx, ry + h * 0.11, 0.9, GREY)
    # ball, flying off the strings
    fill_circle(x + w * 0.68, y + h * 0.22, h * 0.055, (206, 226, 90))
    stroke_arc(x + w * 0.68, y + h * 0.22, h * 0.055, 100, 260, 1.0,
               (250, 250, 246))


# ---------------------------------------------------------------- page
MX = 22.0           # page margin
CW = 980.0          # content width
CREAM = (253, 250, 243)
BODY = (62, 58, 52)

HEROES = [
    (1, "SHENZHEN · CHINA", "OFFICIAL · REUTERS",
     "THREE LEADERS SIGN PEACE DECLARATION",
     "First Trump-Xi-Putin summit, Kylin Villa: 4 points - UN reform, "
     "stable energy, court limits, nuclear talks.", art_summit),
    (2, "THE HAGUE", "OFFICIAL · ICJ / AP",
     "COURT: MYANMAR COMMITTED GENOCIDE",
     "9-6 in The Gambia's Rohingya case, Pres. Iwasawa reading. First "
     "state liable for genocide; reparations due.", art_court),
    (3, "WALL STREET", "REPORTED · REUTERS",
     "DOW LOSES 1,101 IN SIXTH STRAIGHT FALL",
     "S&P -2.02% to 7,175.83; Dow under 50,000, first since June; "
     "Nasdaq -2.25%; VIX ~28.5; all sectors red.", art_chart_fall),
]

ROW2 = [
    (4, "ANTHROPIC · NASDAQ", "REPORTED · NASDAQ",
     "ANT DEBUTS +17% ON DAY ONE",
     "Opened $111.50, closed $97.17; 846m shares, $81.34bn raised.",
     art_anthropic),
    (5, "BERLIN", "REPORTED · REUTERS",
     "30 LEADERS BACK UKRAINE",
     "40 delegations; EU EUR45bn loan on the table; UK pledges 1,000 "
     "strike drones.", art_berlin),
    (6, "THE GULF", "REPORTED · REUTERS / AFP",
     "IRAN DRONES HIT KUWAIT BASE",
     "Bahrain stops a 4th wave in 6 days; tanker hit at Khasab; "
     "1 missing, 11 hurt.", art_gulf),
    (7, "COP31 · ANTALYA", "REPORTED · AFP",
     "DRAFT DROPS FOSSIL FUELS",
     "Draft cut from 144 to 80 paragraphs; 21 issues open; "
     "deadlocked, closes Fri.", art_cop),
    (8, "DR CONGO", "REPORTED · AFRICA CDC",
     "EBOLA DEATHS PASS 5,500",
     "5,568 dead, 11,376 cases; 'not under control'; medics strike "
     "over pay.", art_ebola),
]

ROW3 = [
    (9, "FLORIDA", "REPORTED · NWS / AP",
     "BROWARD SCHOOLS SHUT",
     "12-15in rain floods Hollywood; 300+ rescues; I-95 shut; a roof "
     "falls in.", art_florida),
    (10, "UNITED STATES", "OFFICIAL · COMMERCE DEPT",
     "AI CHIP CURBS TAKE EFFECT",
     "Licences now needed for SG, MY, ID, TH, BR; 12m TPP compute "
     "rule.", art_chip),
    (11, "GTA VI", "REPORTED · BBC",
     "GTA VI LANDS WORLDWIDE",
     "Vice City return after 13 years; Jason & Lucia; $79.99; "
     "$2.3bn tipped.", art_gta),
    (12, "DEEP SPACE", "OFFICIAL · NASA",
     "ONE LIGHT-DAY FROM EARTH",
     "Voyager 1 at 16.1bn miles; signal ~24h each way, 48h round "
     "trip.", art_voyager),
    (13, "TURIN · TENNIS", "REPORTED · ATP",
     "ZVEREV SWEEPS 3-0",
     "Beats Fils 6-4 7-6(8-6) Thu night; Shelton (2-1) also into "
     "semis.", art_tennis),
]

ALSO = [
    "Gold $3,624.62, -2.68%, a 14-month low",
    "Jobless claims 203,000 vs ~197k forecast",
    "Philadelphia Fed 6.3 vs ~20 forecast",
    "Asia: Taiex -3.73%, Hang Seng -1.89%",
    "KOSPI -1.60% in Asia's early rout",
    "Brent ~$91.43 after Wed's $91.95 settle",
    "Houthi threat on Riyadh; debris damage",
    "Senate GOP rejects Iran war-powers cap",
    "Fed minutes hawkish; Dec hike ~96%",
    "ANT grey market ~$98 before the open",
    "Bilaterals: Trump-Xi 1h, Trump-Putin 42m",
    "Trilateral started ~2 hours late",
    "New START lapsed Feb 2026; caps gone",
    "Ebola aid: $1.3bn of $2.9bn released",
    "Declaration silent on Ukraine, Iran",
    "Declaration: more refined oil supply",
    "Declaration: state consent paramount",
    "GTA VI unlocks from NZ at midnight",
    "S&P streak longest since April 2024",
    "Nasdaq-100 15.4% below Oct 6 high",
    "ANT range: high $115.10, low $92.72",
    "Berlin: biggest Ukraine meeting yet",
    "Fort Lauderdale 5.72in; 1959 record",
    "S&P breaks below 200-day average",
]

FIGURES = [
    ("9-6", "ICJ GENOCIDE VOTE"),
    ("-1,101", "DOW POINTS LOST"),
    ("-2.02%", "S&P 500, ONE DAY"),
    ("+17%", "ANT DEBUT CLOSE"),
    ("$81.3BN", "ANTHROPIC RAISED"),
    ("5,500+", "EBOLA DEATHS"),
    ("203,000", "US JOBLESS CLAIMS"),
    ("$3,625", "GOLD, 14-MO LOW"),
]

REGIONS = [
    ("ASIA", 9, RED), ("EUROPE", 7, BLUE), ("MIDEAST", 6, GOLD),
    ("AMERICAS", 8, TEAL), ("AFRICA", 3, BROWN), ("OCEANIA", 1, GREEN),
    ("WORLD", 3, GREY),
]

MAP_ROWS = [
    "    #####          #####################################",
    "  #########       #######################################",
    " ###########       ################  ###################",
    "  #########         ##############    #################",
    "   ########          ############      ###############",
    "    ######            ##########        #############",
    "     ####              ########          ##########",
    "     ###      #         ######            ########       #",
    "      ##               ######              ######",
    "      ###               ####               #####       ##",
    "      ####              ####               ####        ###",
    "       ###              ###                ###         ##",
    "       ####             ###                ##",
    "        ###             ##                 #          ####",
    "        ####            #                              ######",
    "         ###                                            ####",
    "         ####                                            ##",
    "          ##",
    "          #",
]


def panel(x, y, w, h, num, place, tag, head, body, art, hero=False):
    fill_rect(x, y, w, h, PANEL)
    stroke_rect(x, y, w, h, 1.1, RULE)
    if hero:
        pad = 8.0
        fill_rect(x + pad, y + 6, 16, 16, RED)
        draw_text(x + pad + 8, y + 19.5, str(num), 11, CREAM, 1.9,
                  align='c')
        draw_text(x + pad + 22, y + 20, place, 12, INK, 2.0)
        draw_text(x + w - pad, y + 20, tag, 8.4, GREY, 1.1, align='r')
        art(x + pad, y + 26, w - 2 * pad, 64)
        ey = draw_para(x + pad, y + 94, head, 16.5, INK, 2.3,
                       w - 2 * pad, 19.0)
        draw_para(x + pad, ey + 1, body, 10.8, BODY, 1.3, w - 2 * pad,
                  13.6, max_lines=3)
    else:
        pad = 6.0
        fill_rect(x + pad, y + 5, 13, 13, RED)
        draw_text(x + pad + 6.5, y + 15.5, str(num), 9, CREAM, 1.6,
                  align='c')
        draw_text(x + pad + 18, y + 16.5, place, 10, INK, 1.7)
        art(x + pad, y + 21, w - 2 * pad, 32)
        ey = draw_para(x + pad, y + 56, head, 12, INK, 1.9,
                       w - 2 * pad, 14.5)
        draw_para(x + pad, ey, body, 8.8, BODY, 1.1, w - 2 * pad,
                  11.2, max_lines=3)
        draw_text(x + pad, y + h - 4.5, tag, 7.8, GREY, 1.0)


def build():
    # ---- top strip
    draw_text(MX, 30, "THE WORLD IN ONE DAY", 14.5, INK, 2.2)
    draw_text(MX + CW, 30, "37 STORIES · 7 REGIONS", 14.5, RED, 2.2,
              align='r')
    fill_rect(MX, 38, CW, 3.5, RED)
    fill_rect(MX, 44, CW, 1.2, INK)

    # ---- masthead with calendar box
    bx, by, bw, bh = MX, 54.0, 104.0, 88.0
    stroke_rect(bx, by, bw, bh, 2.2, INK)
    fill_rect(bx, by, bw, 10, RED)
    draw_text(bx + bw / 2, 118, "19", 44, INK, 5.5, align='c',
              serif=True)
    draw_text(bx + bw / 2, 136, "NOV 2026 · THU", 10.5, GREY, 1.4,
              align='c')
    mast = "THURSDAY 19 NOVEMBER 2026"
    size = 58.0
    while text_w(mast, size) > 852 and size > 30:
        size -= 2.0
    draw_text(140, 96 + size * 0.35, mast, size, INK, size * 0.145,
              serif=True)
    fill_rect(MX, 147, CW, 1.4, INK)

    # ---- red italic sub-headline
    draw_para(MX, 156, "Three leaders sign a peace declaration in "
              "Shenzhen · World Court rules Myanmar committed genocide "
              "· Wall Street's worst day since June", 17.5, RED, 2.0,
              CW, 22, italic=True, max_lines=2)

    # ---- region bar
    draw_text(MX, 224, "REGIONS", 11, INK, 1.8)
    cx = 104.0
    for name, n, col in REGIONS:
        fill_circle(cx + 4, 219, 3.6, col)
        label = "%s %d" % (name, n)
        draw_text(cx + 12, 224, label, 12.5, INK, 1.7)
        cx += 12 + text_w(label, 12.5) + 24
    fill_rect(MX, 232, CW, 1.0, RULE)

    # ---- the day in figures
    draw_text(MX, 250, "THE DAY IN FIGURES", 11.5, INK, 1.9)
    cell = CW / 8.0
    for i, (num, lab) in enumerate(FIGURES):
        ccx = MX + cell * i + cell / 2
        fsize = 25.0
        while text_w(num, fsize) > cell - 8 and fsize > 14:
            fsize -= 1.0
        draw_text(ccx, 284, num, fsize, RED if i in (1, 2) else INK,
                  3.4, align='c')
        draw_para(ccx, 290, lab, 8.6, GREY, 1.05, cell - 4, 11,
                  align='c', max_lines=2)
    fill_rect(MX, 320, CW, 1.0, RULE)

    # ---- hero row
    for i, (num, place, tag, head, body, art) in enumerate(HEROES):
        panel(MX + i * 330.0, 330, 320, 184, num, place, tag, head,
              body, art, hero=True)

    # ---- two rows of five
    for data, ry in ((ROW2, 524.0), (ROW3, 666.0)):
        for i, (num, place, tag, head, body, art) in enumerate(data):
            panel(MX + i * 197.75, ry, 189, 132, num, place, tag, head,
                  body, art)

    # ---- bottom band: map + legend | also list
    draw_text(MX, 820, "THE DAY ON THE MAP", 11, INK, 1.9)
    mw = 288.0
    cellx = mw / 56.0
    celly = 76.0 / len(MAP_ROWS)
    for ri, row in enumerate(MAP_ROWS):
        for ci, ch in enumerate(row):
            if ch == '#':
                fill_circle(MX + ci * cellx + cellx / 2,
                            828 + ri * celly + celly / 2, 1.5,
                            (90, 96, 110))
    draw_text(MX, 924, "HOW SURE ARE WE?", 10.5, INK, 1.8)
    draw_para(MX, 930, "OFFICIAL - the body itself · REPORTED - named "
              "sources agree · CLAIM - one side's account only", 9.2,
              BODY, 1.15, 288, 12.5, max_lines=3)
    stroke_line(322, 812, 322, 962, 1.0, RULE)

    ax = 334.0
    draw_text(ax, 820, "ALSO ON THURSDAY", 11, INK, 1.9)
    colw = 330.0
    for i, item in enumerate(ALSO):
        col = i // 12
        rowi = i % 12
        ix = ax + col * (colw + 8)
        iy = 838 + rowi * 11.2
        draw_text(ix, iy, str(14 + i), 9.2, RED, 1.7)
        draw_text(ix + 24, iy, item, 9.2, BODY, 1.15)

    # ---- date check footer
    fill_rect(MX, 970, CW, 2.0, RED)
    fill_rect(MX + 0, 982, 8, 8, RED)
    draw_para(MX + 14, 978, "DATE CHECK - LEFT OUT AS EARLIER NEWS "
              "(WED 18 NOV): Anthropic's $83 pricing · Jeffries "
              "nomination 251-11 · Hegseth's Venezuela deal · EU "
              "EUR45bn Ukraine loan proposal · Voyager crossing one "
              "light-day. NOT YET HAPPENED: COP31's close (Fri 20 Nov). "
              "LEFT OUT AS UNVERIFIED: North Korea missile claim · "
              "Crimean Bridge claim.", 9.2, BODY, 1.15, CW - 14, 12.5,
              max_lines=3)


# ---------------------------------------------------------------- out
def downscale():
    """Box-filter the 4096x4096 framebuffer down to 1024x1024."""
    out = bytearray(W * W * 3)
    for oy in range(W):
        acc = None
        for sy in range(oy * SS, oy * SS + SS):
            off = sy * W4 * 3
            row = FB[off:off + W4 * 3]
            if acc is None:
                acc = list(row)
            else:
                acc = list(map(add, acc, row))
        orow = bytearray(W * 3)
        for c in range(3):
            ch = acc[c::3]
            vals = [(a + b + d + e) // 16 for a, b, d, e in
                    zip(ch[0::4], ch[1::4], ch[2::4], ch[3::4])]
            orow[c::3] = bytes(vals)
        out[oy * W * 3:(oy + 1) * W * 3] = orow
    return out


def save_png(img, path):
    raw = bytearray()
    stride = W * 3
    for yy in range(W):
        raw.append(0)
        raw += img[yy * stride:(yy + 1) * stride]

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', W, W, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 6))
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


def main():
    build()
    img = downscale()
    outdir = os.environ.get('MAKEFUN_OUTPUT_DIR') or '/output'
    os.makedirs(outdir, exist_ok=True)
    save_png(img, os.path.join(outdir, 'entry.png'))


if __name__ == '__main__':
    main()
