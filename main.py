#!/usr/bin/env python3
"""Draw Thursday 19 November 2026's world news as a single newspaper
front page and write it to /output/entry.png (1024x1024 PNG).

LATE EDITION (round 2, revised Friday 20 November): round 1 was drawn
while the day was still unfolding. This revision replaces the three
panels whose stories have since landed with their actual outcomes:

  lead  - the Shenzhen trilateral is OVER: Trump, Xi and Putin signed
          a four-point joint "Declaration toward Peace" (UN reform,
          refined-oil supply, ICC jurisdiction limits, nuclear-risk
          dialogue). No breakthrough: Ukraine and Iran untouched, no
          nuclear cuts. Separately, Trump and Xi extended the US-China
          trade truce (terms undisclosed).
  1     - MARKETS: Thursday's Wall Street close was a rout: S&P 500
          -2.02% (sixth straight loss), Dow -1,101 to 49,097, first
          close below 50,000 since June, Nasdaq -2.25%, VIX about 28.5.
          The early Anthropic-debut rally faded by late morning.
  2     - TECH: Anthropic's ANT debut is DONE: priced $83, opened
          $111.50 (+34%), high $115.10, closed $97.17 (+17%); about
          846m shares traded, Nasdaq's most-traded name; $81.34bn
          raised (980m shares at $83).
  3     - GULF: Wednesday's events stand (Iran drones at Ali Al-Salem
          airbase in Kuwait, Bahrain intercepted attacks again, tanker
          struck near Khasab in Hormuz); no new strikes Thursday;
          Gulf states, Pakistan and Turkey push diplomacy.
  4     - CLIMATE: COP31's Thursday draft cover decision slimmed from
          144 paragraphs to 80 and removed EVERY fossil-fuel reference;
          still a draft, not adopted, as the summit closes Friday.
  5     - HEALTH: Ebola deaths pass 5,500 in DR Congo; 11,000+ cases;
          still not under control.
  6     - POLITICS: Democrats nominate Hakeem Jeffries for Speaker,
          251-11; would be the first Black Speaker (vote Jan 3).
  also  - US AI-chip export curbs took effect Thu; Zverev sweeps his
          Turin group 3-0 and Shelton joins him in the semifinals;
          Voyager 1 one light-day out; GTA VI rolls out worldwide.
  The unverified North Korea missile claim stays excluded.

Standard library only. Everything is drawn by this program: a small
PNG encoder (zlib + struct), a hand-drawn 5x7 bitmap font, and all
shapes (rectangles, lines, circles, polygons) used for the masthead,
the Shenzhen summit hero illustration and the six story panels.

Deterministic: no wall clock, no randomness, no dict-order dependence.
Running it twice produces byte-identical output.
"""

import math
import os
import struct
import zlib

# ---------------------------------------------------------------- canvas

W, H = 1024, 1024

PAPER = (246, 241, 230)      # newsprint cream
PAPER2 = (255, 253, 245)     # lighter panel paper
INK = (20, 20, 20)           # near-black text
NAVY = (12, 40, 70)          # masthead blue
NAVY2 = (26, 64, 104)
RED = (176, 32, 32)          # headline red
RED2 = (148, 22, 22)
TEAL = (13, 92, 86)
GOLD = (174, 122, 20)
GREY = (88, 86, 80)          # body grey
LINE = (38, 38, 38)
SKY1 = (168, 200, 228)
SKY2 = (206, 226, 240)
WOOD = (122, 84, 48)
WOOD2 = (96, 64, 36)
GREEN = (22, 120, 60)
GREEN2 = (16, 92, 46)
STEEL = (72, 76, 82)
STEEL2 = (50, 54, 60)
SMOKE = (148, 148, 146)
WHITE = (255, 255, 255)
YELLOW = (255, 222, 0)


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.px), 3):
            self.px[i] = r
            self.px[i + 1] = g
            self.px[i + 2] = b

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def hline(self, x0, x1, y, c, t=1):
        for yy in range(y, y + t):
            for xx in range(min(x0, x1), max(x0, x1) + 1):
                self.set(xx, yy, c)

    def vline(self, x, y0, y1, c, t=1):
        for xx in range(x, x + t):
            for yy in range(min(y0, y1), max(y0, y1) + 1):
                self.set(xx, yy, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        """Bresenham line, thickness t (square brush)."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        half = t // 2
        while True:
            for oy in range(-half, half + 1):
                for ox in range(-half, half + 1):
                    self.set(x + ox, y + oy, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, c, fill=True):
        if fill:
            for yy in range(cy - r, cy + r + 1):
                dy = yy - cy
                if abs(dy) <= r:
                    dx = int((r * r - dy * dy) ** 0.5)
                    for xx in range(cx - dx, cx + dx + 1):
                        self.set(xx, yy, c)
        else:
            steps = max(8, int(6.28 * r))
            for k in range(steps):
                a = 6.283185307179586 * k / steps
                self.set(cx + int(r * math.cos(a)),
                         cy + int(r * math.sin(a)), c)

    def poly(self, pts, c):
        """Fill a polygon by scanline (pts = list of (x, y))."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            if len(xs) >= 2:
                xs.sort()
                for k in range(0, len(xs) - 1, 2):
                    for xx in range(int(xs[k]), int(xs[k + 1]) + 1):
                        self.set(xx, y, c)

    def disc(self, cx, cy, r, c):
        self.circle(cx, cy, r, c, fill=True)


# ---------------------------------------------------------------- font
# Hand-drawn 5x7 bitmap font. Each glyph is 7 rows of 5 characters,
# '#' = ink, '.' = blank. Uppercase, digits and punctuation; all
# poster text is set in capitals.

FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '-': (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    '(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    '/': ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    '%': ("##...", "##.#.", "...#.", "..#..", ".#...", ".#.##", "...##"),
    '$': ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    '+': (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    '=': (".....", ".....", ".###.", ".....", ".###.", ".....", "....."),
    '&': (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
}

CHAR_W = 6  # advance per character, in font units (5 glyph + 1 space)


def text_width(s, scale):
    return len(s) * CHAR_W * scale - scale


def draw_text(cv, s, x, y, scale, color, align="left"):
    """Draw uppercase text; returns the x of the right edge + scale."""
    w = text_width(s, scale)
    if align == "center":
        x = x - w // 2
    elif align == "right":
        x = x - w
    cx = x
    for ch in s:
        glyph = FONT.get(ch, FONT[' '])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '#':
                    cv.rect(cx + col * scale, y + row * scale,
                            scale, scale, color)
        cx += CHAR_W * scale
    return x + w


def wrap_text(s, max_chars):
    """Greedy word wrap; returns a list of lines."""
    words = s.split()
    lines = []
    cur = ""
    for word in words:
        if cur == "":
            cur = word
        elif len(cur) + 1 + len(word) <= max_chars:
            cur = cur + " " + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, s, x, y, max_chars, scale, color, line_h=None):
    """Draw a wrapped paragraph; returns y just below the last line."""
    if line_h is None:
        line_h = 7 * scale + 3 * scale // 2
    for line in wrap_text(s, max_chars):
        draw_text(cv, line, x, y, scale, color)
        y += line_h
    return y


# ---------------------------------------------------------------- png

def write_png(path, cv):
    raw = bytearray()
    row_len = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * row_len:(y + 1) * row_len]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        c += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- flags

def draw_flag_us(cv, x, y, w, h):
    """Stars and stripes, simplified."""
    stripe = max(2, h // 13)
    for i in range(13):
        if i * stripe >= h:
            break
        cv.rect(x, y + i * stripe, w, stripe,
                RED if i % 2 == 0 else WHITE)
    cw = int(w * 0.4)
    ch = stripe * 7
    cv.rect(x, y, cw, ch, NAVY)
    for dy in (4, 10, 16):
        for dx in (5, 13, 21):
            if dx < cw - 2 and dy < ch - 2:
                cv.disc(x + dx, y + dy, 1, WHITE)


def draw_flag_cn(cv, x, y, w, h):
    """China: red field, one big star, four small stars."""
    cv.rect(x, y, w, h, RED2)
    cv.disc(x + w // 5, y + h // 4, 5, YELLOW)
    for dx, dy in ((w // 2, h // 6), (w * 3 // 5, h // 4),
                   (w * 3 // 5, h // 2), (w // 2, h * 3 // 5)):
        cv.disc(x + dx, y + dy, 2, YELLOW)


def draw_flag_ru(cv, x, y, w, h):
    """Russia: white / blue / red horizontal bands."""
    cv.rect(x, y, w, h // 3 + 1, WHITE)
    cv.rect(x, y + h // 3, w, h // 3 + 1, (0, 57, 166))
    cv.rect(x, y + 2 * h // 3, w, h - 2 * h // 3, (213, 0, 50))


# ---------------------------------------------------------------- icons
# Small flat illustrations, one per story panel. Each draws inside a
# box (x, y, w, h) and uses only rect/line/circle/poly.

def icon_tanker(cv, x, y, w, h):
    """Oil tanker in the Strait, flame from a hit. Fits its box."""
    cx = x + w // 2
    # sea (bottom of the box)
    cv.rect(x, y + 36, w, h - 36, (38, 98, 138))
    cv.hline(x + 8, x + w - 8, y + 42, (24, 74, 110), 2)
    cv.hline(x + 30, x + w - 30, y + 47, (24, 74, 110), 2)
    # hull
    cv.poly([(cx - 78, y + 20), (cx + 78, y + 20), (cx + 62, y + 36),
             (cx - 62, y + 36)], STEEL2)
    cv.rect(cx - 78, y + 20, 156, 3, RED)
    # deck + funnel
    cv.rect(cx - 52, y + 10, 40, 10, (120, 90, 60))
    cv.rect(cx + 34, y + 6, 14, 14, (200, 60, 40))
    cv.rect(cx + 34, y + 6, 14, 3, INK)
    # flame from the hit, mid-ship
    cv.poly([(cx - 6, y + 20), (cx + 2, y + 2), (cx + 10, y + 20)],
            (255, 140, 20))
    cv.poly([(cx - 2, y + 20), (cx + 2, y + 10), (cx + 6, y + 20)],
            YELLOW)


def icon_chart_down(cv, x, y, w, h):
    """Falling market line over bars, breaking a floor. Fits its box."""
    cx = x + w // 2
    # bars
    base = y + 44
    for i, bh in enumerate((8, 13, 7, 16, 10, 5)):
        bx = cx - 66 + i * 22
        cv.rect(bx, base - bh, 12, bh, (150, 170, 190))
    # axes
    cv.hline(cx - 72, cx + 72, base, INK, 2)
    cv.vline(cx - 72, y + 6, base, INK, 2)
    # the 50,000 floor, dashed, snapped where the line crosses it
    for dx in range(cx - 66, cx + 8, 12):
        cv.hline(dx, dx + 6, y + 30, GOLD, 2)
    for dx in range(cx + 26, cx + 70, 12):
        cv.hline(dx, dx + 6, y + 34, GOLD, 2)
    # falling line: morning rally, then the rout
    pts = [(cx - 66, y + 16), (cx - 40, y + 8), (cx - 14, y + 18),
           (cx + 12, y + 30), (cx + 38, y + 36), (cx + 64, y + 43)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], RED, 4)
    # down arrowhead
    cv.poly([(cx + 64, y + 43), (cx + 52, y + 43), (cx + 64, y + 31)],
            RED)
    draw_text(cv, "50,000", cx - 70, y + 21, 1, GOLD)


def icon_chip_ant(cv, x, y, w, h):
    """AI chip with ANT ticker and the $97.17 close tag. Fits its box."""
    cx = x + w // 2 - 16
    cy = y + h // 2
    s = 30
    for i in range(4):
        off = -11 + i * 7
        cv.rect(cx - s // 2 - 6, cy + off, 6, 3, GREEN2)
        cv.rect(cx + s // 2, cy + off, 6, 3, GREEN2)
        cv.rect(cx + off, cy - s // 2 - 6, 3, 6, GREEN2)
        cv.rect(cx + off, cy + s // 2, 3, 6, GREEN2)
    cv.rect(cx - s // 2, cy - s // 2, s, s, GREEN)
    cv.rect(cx - s // 2, cy - s // 2, s, 4, GREEN2)
    cv.rect(cx - 13, cy - 8, 26, 16, (225, 248, 228))
    draw_text(cv, "ANT", cx - 11, cy - 5, 2, INK)
    # closing-price tag, bottom right: $97.17, still +17% on the day
    tx = x + w - 92
    ty = y + h - 20
    cv.rect(tx, ty, 84, 18, GREEN2)
    draw_text(cv, "$97.17", tx + 7, ty + 3, 2, WHITE)
    # the fade: up to the $111.50 open, then down into the close
    ax = x + w - 84
    ay = y + 4
    cv.line(ax, ay + 14, ax + 16, ay + 2, GREEN, 4)
    cv.line(ax + 16, ay + 2, ax + 34, ay + 12, RED, 4)
    cv.poly([(ax + 34, ay + 12), (ax + 22, ay + 12), (ax + 34, ay + 2)],
            RED)
    draw_text(cv, "+34%", ax + 44, ay + 2, 1, GREEN2)
    draw_text(cv, "OPEN", ax + 44, ay + 11, 1, GREY)


def icon_climate(cv, x, y, w, h):
    """Draft document with the fossil-fuel drop struck out. Fits box."""
    cx = x + w // 2
    # the draft page, left of centre
    px, py, pw, ph = cx - 108, y + 3, 62, 44
    cv.rect(px, py, pw, ph, WHITE)
    cv.rect(px, py, pw, 2, LINE)
    cv.rect(px, py + ph - 2, pw, 2, LINE)
    cv.rect(px, py, 2, ph, LINE)
    cv.rect(px + pw - 2, py, 2, ph, LINE)
    for i in range(4):
        cv.hline(px + 8, px + pw - 8, py + 9 + i * 9, SMOKE, 2)
    draw_text(cv, "DRAFT", px + 8, py + ph - 12, 1, GREY)
    # the fuel drop, right of centre, struck through in red
    dx, dy = cx + 42, y + 26
    cv.poly([(dx, y + 6), (dx - 11, dy + 4), (dx + 11, dy + 4)], STEEL2)
    cv.disc(dx, dy + 6, 11, STEEL2)
    cv.disc(dx - 3, dy + 4, 3, (120, 126, 134))
    cv.line(dx - 18, y + 44, dx + 18, y + 8, RED, 5)
    draw_text(cv, "FOSSIL", dx + 30, y + 12, 2, RED2)
    draw_text(cv, "CUT", dx + 30, y + 28, 2, RED2)


def icon_virus(cv, x, y, w, h):
    """Ebola virus: spiked ball. Fits its box."""
    cx = x + w // 2
    cy = y + h // 2
    for k in range(12):
        a = 6.283185307179586 * k / 12
        x1 = cx + int(14 * math.cos(a))
        y1 = cy + int(14 * math.sin(a))
        x2 = cx + int(21 * math.cos(a))
        y2 = cy + int(21 * math.sin(a))
        cv.line(x1, y1, x2, y2, RED2, 3)
        cv.disc(x2, y2, 2, RED2)
    cv.disc(cx, cy, 14, RED)
    cv.disc(cx - 5, cy - 5, 4, (255, 120, 120))
    cv.disc(cx + 5, cy + 4, 2, (255, 150, 150))
    draw_text(cv, "5,500+", cx + 32, cy - 7, 2, RED2)


def icon_capitol(cv, x, y, w, h):
    """US Capitol dome + columns. Fits its box."""
    cx = x + w // 2
    base = y + h - 4
    cv.rect(cx - 56, base - 26, 112, 26, (118, 92, 54))
    cv.rect(cx - 56, base - 26, 112, 4, (94, 72, 42))
    cv.disc(cx, base - 26, 12, (94, 72, 42))
    cv.rect(cx - 12, base - 28, 24, 4, (94, 72, 42))
    cv.rect(cx - 1, base - 40, 3, 6, GOLD)
    cv.disc(cx, base - 42, 2, GOLD)
    for dx in (-42, -21, 0, 21, 42):
        cv.rect(cx + dx - 3, base - 20, 6, 20, PAPER2)
    cv.rect(cx - 50, base - 4, 100, 4, (94, 72, 42))
    # vote tally tag, top right
    cv.rect(cx + 34, y + 4, 78, 16, NAVY2)
    draw_text(cv, "251-11", cx + 38, y + 7, 2, WHITE)


# ---------------------------------------------------------------- hero

def draw_hero(cv, x, y, w, h):
    """Shenzhen summit: three flags over the table at Kylin Villa,
    the signed declaration lying on the table."""
    # sky bands
    cv.rect(x, y, w, h // 2, SKY1)
    cv.rect(x, y + h // 2, w, h - h // 2, SKY2)
    # distant hills
    cv.poly([(x, y + h - 60), (x + 200, y + h - 110),
             (x + 420, y + h - 60)], (140, 175, 200))
    cv.poly([(x + w - 420, y + h - 60), (x + w - 200, y + h - 104),
             (x + w, y + h - 60)], (140, 175, 200))
    # ground
    cv.rect(x, y + h - 60, w, 60, (196, 214, 196))
    # three flag poles
    fw, fh = 120, 72
    gap = 46
    total = fw * 3 + gap * 2
    sx = x + (w - total) // 2
    sy = y + 18
    pole_y = sy + fh
    for i, fn in enumerate((draw_flag_us, draw_flag_cn, draw_flag_ru)):
        fx = sx + i * (fw + gap)
        fn(cv, fx, sy, fw, fh)
        cv.rect(fx, sy, fw, 1, LINE)
        cv.rect(fx, sy + fh - 1, fw, 1, LINE)
        cv.rect(fx, sy, 1, fh, LINE)
        cv.rect(fx + fw - 1, sy, 1, fh, LINE)
        cv.vline(fx - 3, sy - 6, pole_y + 62, STEEL2, 3)
        cv.disc(fx - 2, sy - 8, 3, GOLD)
    # long summit table
    ty = y + h - 44
    cv.rect(x + 60, ty, w - 120, 10, WOOD)
    cv.rect(x + 60, ty + 10, w - 120, 4, WOOD2)
    cv.rect(x + 80, ty + 14, 10, 22, WOOD2)
    cv.rect(x + w - 90, ty + 14, 10, 22, WOOD2)
    # three chairs behind the table
    for i in range(3):
        chx = sx + i * (fw + gap) + fw // 2 - 14
        cv.rect(chx, ty - 26, 28, 26, NAVY2)
        cv.rect(chx, ty - 26, 28, 4, NAVY)
    # name plates on the table
    for i, tag in enumerate(("USA", "CHN", "RUS")):
        px = sx + i * (fw + gap) + fw // 2 - 16
        cv.rect(px, ty - 12, 32, 10, PAPER2)
        draw_text(cv, tag, px + 4, ty - 10, 1, INK)
    # the signed declaration on the table, red seal on it; placed
    # right of centre so all three name plates stay readable
    dx = x + w // 2 + 58
    cv.rect(dx, ty - 15, 42, 13, WHITE)
    cv.rect(dx, ty - 15, 42, 1, LINE)
    cv.rect(dx, ty - 3, 42, 1, LINE)
    cv.hline(dx + 5, dx + 26, ty - 11, SMOKE, 1)
    cv.hline(dx + 5, dx + 26, ty - 8, SMOKE, 1)
    cv.disc(dx + 34, ty - 8, 4, RED)
    # "DECLARATION SIGNED" tag
    cv.rect(x + 14, y + 10, 240, 26, RED)
    draw_text(cv, "DECLARATION SIGNED", x + 24, y + 16, 2, WHITE)


# ---------------------------------------------------------------- page

PANELS = [
    # (kicker, kicker colour, headline, body, icon fn)
    ("MARKETS", NAVY, "WALL STREET SINKS",
     "S&P -2.02%, SIXTH STRAIGHT LOSS. DOW -1,101 BELOW 50,000. "
     "NASDAQ -2.25%. VIX 28.5.",
     icon_chart_down),
    ("TECH", GREEN, "ANTHROPIC FADES TO +17%",
     "OPENS $111.50, CLOSES $97.17 (+17%). 846M SHARES TRADED. "
     "$81.3BN RAISED.",
     icon_chip_ant),
    ("GULF", RED2, "IRAN HITS US BASE IN KUWAIT",
     "ALI AL-SALEM DRONED WED. BAHRAIN HIT AGAIN. TANKER STRUCK "
     "IN HORMUZ. NO NEW STRIKES THU.",
     icon_tanker),
    ("CLIMATE", TEAL, "COP31 DROPS FOSSIL FUELS",
     "DRAFT SLIMMED 144 TO 80, EVERY FOSSIL-FUEL LINE CUT. "
     "STILL NOT ADOPTED.",
     icon_climate),
    ("HEALTH", RED, "EBOLA DEATHS PASS 5,500",
     "11,000+ CASES IN CONGO. AFRICA CDC: STILL NOT UNDER CONTROL.",
     icon_virus),
    ("POLITICS", NAVY2, "JEFFRIES PICKED FOR SPEAKER",
     "DEMOCRATS VOTE 251-11, WOULD BE FIRST BLACK SPEAKER. VOTE JAN 3.",
     icon_capitol),
]


def draw_panel(cv, x, y, w, h, kicker, kcolor, headline, body, icon):
    cv.rect(x, y, w, h, PAPER2)
    # border (2px)
    cv.rect(x, y, w, 2, LINE)
    cv.rect(x, y + h - 2, w, 2, LINE)
    cv.rect(x, y, 2, h, LINE)
    cv.rect(x + w - 2, y, 2, h, LINE)
    # kicker band
    cv.rect(x + 2, y + 2, w - 4, 26, kcolor)
    draw_text(cv, kicker, x + 12, y + 8, 2, WHITE)
    # icon
    icon(cv, x + 10, y + 32, w - 20, 50)
    # headline (up to 2 lines)
    max_chars = (w - 24) // (CHAR_W * 3)
    lines = wrap_text(headline, max_chars)
    ty = y + 88
    for line in lines[:2]:
        draw_text(cv, line, x + 12, ty, 3, INK)
        ty += 22
    # body (up to 4 lines)
    max_body = (w - 24) // (CHAR_W * 2)
    by = ty + 4
    for line in wrap_text(body, max_body)[:4]:
        draw_text(cv, line, x + 12, by, 2, GREY)
        by += 15


def build():
    cv = Canvas(W, H, PAPER)

    # ---- masthead
    cv.rect(0, 0, W, 108, NAVY)
    cv.rect(0, 108, W, 4, RED)
    draw_text(cv, "THE WORLD IN ONE DAY", W // 2, 22, 6, WHITE,
              align="center")
    draw_text(cv, "LATE EDITION - THE DAY'S OUTCOMES, UPDATED",
              W // 2, 82, 2, (190, 205, 220), align="center")

    # ---- date banner
    cv.rect(24, 124, W - 48, 44, PAPER2)
    cv.rect(24, 124, W - 48, 2, LINE)
    cv.rect(24, 166, W - 48, 2, LINE)
    draw_text(cv, "THURSDAY 19 NOVEMBER 2026", W // 2, 132, 4, RED,
              align="center")

    # ---- hero: summit illustration + headline
    hx, hy, hw, hh = 24, 180, W - 48, 304
    cv.rect(hx, hy, hw, hh, PAPER2)
    draw_hero(cv, hx + 2, hy + 2, hw - 4, 188)
    # headline block under the illustration
    ty = hy + 198
    draw_text(cv, "TRUMP, XI AND PUTIN SIGN", hx + 14, ty, 5, INK)
    draw_text(cv, "PEACE DECLARATION", hx + 14, ty + 38, 5, RED)
    draw_para(cv,
              "4 POINTS: UN REFORM, OIL SUPPLY, ICC LIMITS, NUCLEAR "
              "TALKS. NO DEAL ON UKRAINE. US-CHINA TRADE TRUCE "
              "EXTENDED.",
              hx + 14, ty + 82, (hw - 28) // (CHAR_W * 2), 2, GREY)

    # ---- story grid: 3 columns x 2 rows
    gx, gy = 24, 496
    pw, ph = 318, 200
    gap = 11
    for i, (kicker, kcolor, headline, body, icon) in enumerate(PANELS):
        px = gx + (i % 3) * (pw + gap)
        py = gy + (i // 3) * (ph + gap)
        draw_panel(cv, px, py, pw, ph, kicker, kcolor, headline, body, icon)

    # ---- footer strip
    fy = gy + 2 * ph + gap + 12
    cv.rect(24, fy, W - 48, 2, LINE)
    draw_para(cv,
              "ALSO: CHIP CURBS TAKE EFFECT - LICENCES FOR AI CHIPS. "
              "ZVEREV SWEEPS GROUP 3-0, SHELTON IN SEMIS. VOYAGER 1 "
              "ONE LIGHT-DAY OUT. GTA VI ROLLS OUT WORLDWIDE.",
              24, fy + 12, (W - 48) // (CHAR_W * 2), 2, INK)
    # ---- bottom credit bar
    cv.rect(0, 988, W, 36, NAVY)
    draw_text(cv, "DRAWN IN CODE - NO PHOTOGRAPHS - THE WORLD IN ONE DAY",
              W // 2, 997, 2, (190, 205, 220), align="center")
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    cv = build()
    size = write_png(path, cv)
    print(f"wrote {path} ({cv.w}x{cv.h}, {size} bytes)")


if __name__ == "__main__":
    main()
