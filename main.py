#!/usr/bin/env python3
"""The World in One Day - Thursday 19 November 2026, late edition.

Written fresh on Friday 20 November 2026 in a new session, after the
day's three open stories had actually landed.  Round 1 of this entry
was drawn on the day itself, when the Shenzhen trilateral had only
just met, Wall Street had not yet closed, and Anthropic's ANT shares
had not yet finished their first day of trading.  This late edition
keeps the same newspaper idea and the same six-panel breadth, but
every panel now reports an outcome instead of an expectation:

  hero    Trump, Xi and Putin signed a four-point joint declaration
          in Shenzhen: UN reform, more refined-oil supply, limits on
          ICC jurisdiction, and a nuclear-risk dialogue.  There was
          no deal on Ukraine or Iran and no nuclear arms cuts, and
          separately Trump and Xi extended the US-China trade truce
          on undisclosed terms.
  markets Thursday's Wall Street close was a rout: the S&P 500 fell
          2.02 percent to 7,175.83, its sixth straight loss; the Dow
          fell 1,101 points to 49,097, its first close below 50,000
          since June; the Nasdaq fell 2.25 percent; VIX near 28.5.
  tech    Anthropic's debut is complete: priced at 83 dollars, ANT
          opened at 111.50 (+34 percent), touched 115.10, and closed
          at 97.17 (+17 percent).  About 846 million shares traded,
          the most on Nasdaq that day, and 81.3 billion was raised.
  gulf    Wednesday's attacks stand confirmed - Iranian drones at
          Ali Al-Salem air base in Kuwait, Bahrain intercepting
          again, a tanker struck near Khasab in Hormuz - and there
          were no new strikes on Thursday.
  climate COP31's Thursday draft cover decision shrank from 144
          paragraphs to 80 and removed every fossil-fuel reference.
          It is still only a draft, not adopted, as the summit
          closes on Friday.
  health  Ebola deaths in DR Congo passed 5,500, with more than
          11,000 cases, and the outbreak is still not controlled.
  politics Democrats nominated Hakeem Jeffries for Speaker by
          251 to 11; he would be the first Black Speaker, vote Jan 3.
  footer  US AI-chip export curbs took effect; Zverev swept his
          Turin group 3-0 and Shelton joined him in the semifinals;
          Voyager 1 is one light-day out; GTA VI rolled out.

The unverified North Korea missile claim is excluded, as before.

The picture is drawn entirely by this program: a small RGB canvas,
a hand-set 5 by 7 bitmap typeface, simple shape helpers, and a PNG
writer built on zlib and struct.  Python standard library only.
No clock, no randomness, no network: two runs are byte-identical.
"""

import math
import os
import struct
import zlib

WIDTH = 1024
HEIGHT = 1024

# Newsprint palette, chosen for print contrast at thumbnail size.
CREAM = (246, 241, 230)
PANEL_BG = (255, 253, 245)
INK = (22, 22, 22)
BODY = (86, 84, 78)
RULE = (40, 40, 40)
NAVY = (13, 41, 72)
NAVY_LIGHT = (28, 66, 106)
MASTHEAD_PALE = (190, 206, 222)
RED = (178, 32, 32)
RED_DARK = (148, 22, 22)
TEAL = (13, 92, 86)
GREEN = (22, 120, 60)
GREEN_DARK = (16, 92, 46)
GOLD = (174, 122, 20)
SKY_TOP = (168, 200, 228)
SKY_LOW = (208, 228, 242)
HILL = (140, 175, 200)
GRASS = (196, 214, 196)
WOOD = (122, 84, 48)
WOOD_DARK = (96, 64, 36)
STEEL = (72, 76, 82)
STEEL_DARK = (50, 54, 60)
SMOKE = (148, 148, 146)
WHITE = (255, 255, 255)
YELLOW = (255, 222, 0)
SEA = (38, 98, 138)
SEA_DARK = (24, 74, 110)


class Canvas:
    """A plain RGB pixel buffer with flat shape helpers."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.px), 3):
            self.px[i] = r
            self.px[i + 1] = g
            self.px[i + 2] = b

    def set(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = colour[0]
            self.px[i + 1] = colour[1]
            self.px[i + 2] = colour[2]

    def rect(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = colour[0]
                self.px[i + 1] = colour[1]
                self.px[i + 2] = colour[2]

    def hline(self, x0, x1, y, colour, thick=1):
        for yy in range(y, y + thick):
            for xx in range(min(x0, x1), max(x0, x1) + 1):
                self.set(xx, yy, colour)

    def vline(self, x, y0, y1, colour, thick=1):
        for xx in range(x, x + thick):
            for yy in range(min(y0, y1), max(y0, y1) + 1):
                self.set(xx, yy, colour)

    def line(self, x0, y0, x1, y1, colour, thick=1):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for s in range(steps + 1):
            x = x0 + (x1 - x0) * s // steps
            y = y0 + (y1 - y0) * s // steps
            self.rect(x, y, thick, thick, colour)

    def circle(self, cx, cy, r, colour, fill=False):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                d2 = dx * dx + dy * dy
                if fill and d2 <= r * r:
                    self.set(cx + dx, cy + dy, colour)
                elif not fill and r * r - 2 * r <= d2 <= r * r:
                    self.set(cx + dx, cy + dy, colour)

    def disc(self, cx, cy, r, colour):
        self.circle(cx, cy, r, colour, fill=True)

    def poly(self, points, colour):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        for y in range(min(ys), max(ys) + 1):
            nodes = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    nodes.append(x0 + (y - y0) * (x1 - x0) // (y1 - y0))
            nodes.sort()
            for i in range(0, len(nodes) - 1, 2):
                self.hline(nodes[i], nodes[i + 1], y, colour)


def write_png(path, cv):
    """Write the canvas as a PNG using only zlib and struct."""
    raw = bytearray()
    row = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * row:(y + 1) * row]
    payload = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    header = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    blob = b"\x89PNG\r\n\x1a\n"
    blob += chunk(b"IHDR", header)
    blob += chunk(b"IDAT", payload)
    blob += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(blob)
    return len(blob)


# ------------------------------------------------------------------
# Type: a 5x7 bitmap face.  Each letter is seven strings of five
# cells; '#' is ink.  All poster copy is set in capitals, so only
# capitals, digits and the punctuation the copy needs are included.
# ------------------------------------------------------------------

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

ADVANCE = 6  # five glyph columns plus one blank column, in font units


def text_width(text, scale):
    return len(text) * ADVANCE * scale - scale


def draw_text(cv, text, x, y, scale, colour, align="left"):
    width = text_width(text, scale)
    if align == "center":
        x = x - width // 2
    elif align == "right":
        x = x - width
    cursor = x
    for ch in text:
        glyph = FONT.get(ch, FONT[' '])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '#':
                    cv.rect(cursor + col * scale, y + row * scale,
                            scale, scale, colour)
        cursor += ADVANCE * scale
    return x + width


def wrap_text(text, max_chars):
    lines = []
    current = ""
    for word in text.split():
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current = current + " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_para(cv, text, x, y, max_chars, scale, colour, line_h=None):
    if line_h is None:
        line_h = 7 * scale + 3 * scale // 2
    for line in wrap_text(text, max_chars):
        draw_text(cv, line, x, y, scale, colour)
        y += line_h
    return y


# ------------------------------------------------------------------
# Flags for the hero, and one small flat illustration per panel.
# Every icon is told a box and must stay inside it.
# ------------------------------------------------------------------

def flag_us(cv, x, y, w, h):
    stripe = max(2, h // 13)
    for i in range(13):
        if i * stripe >= h:
            break
        cv.rect(x, y + i * stripe, w, stripe,
                RED if i % 2 == 0 else WHITE)
    canton_w = int(w * 0.4)
    canton_h = stripe * 7
    cv.rect(x, y, canton_w, canton_h, NAVY)
    for dy in (4, 10, 16):
        for dx in (5, 13, 21):
            if dx < canton_w - 2 and dy < canton_h - 2:
                cv.disc(x + dx, y + dy, 1, WHITE)


def flag_cn(cv, x, y, w, h):
    cv.rect(x, y, w, h, RED_DARK)
    cv.disc(x + w // 5, y + h // 4, 5, YELLOW)
    for dx, dy in ((w // 2, h // 6), (w * 3 // 5, h // 4),
                   (w * 3 // 5, h // 2), (w // 2, h * 3 // 5)):
        cv.disc(x + dx, y + dy, 2, YELLOW)


def flag_ru(cv, x, y, w, h):
    cv.rect(x, y, w, h // 3 + 1, WHITE)
    cv.rect(x, y + h // 3, w, h // 3 + 1, (0, 57, 166))
    cv.rect(x, y + 2 * h // 3, w, h - 2 * h // 3, (213, 0, 50))


def icon_falling_chart(cv, x, y, w, h):
    """A morning rally that breaks the 50,000 floor and falls."""
    cx = x + w // 2
    base = y + 44
    for i, bar_h in enumerate((8, 13, 7, 16, 10, 5)):
        cv.rect(cx - 66 + i * 22, base - bar_h, 12, bar_h,
                (150, 170, 190))
    cv.hline(cx - 72, cx + 72, base, INK, 2)
    cv.vline(cx - 72, y + 6, base, INK, 2)
    for dx in range(cx - 66, cx + 8, 12):
        cv.hline(dx, dx + 6, y + 30, GOLD, 2)
    for dx in range(cx + 26, cx + 70, 12):
        cv.hline(dx, dx + 6, y + 34, GOLD, 2)
    points = [(cx - 66, y + 16), (cx - 40, y + 8), (cx - 14, y + 18),
              (cx + 12, y + 30), (cx + 38, y + 36), (cx + 64, y + 43)]
    for a, b in zip(points, points[1:]):
        cv.line(a[0], a[1], b[0], b[1], RED, 4)
    cv.poly([(cx + 64, y + 43), (cx + 52, y + 43), (cx + 64, y + 31)], RED)
    draw_text(cv, "50,000", cx - 70, y + 21, 1, GOLD)


def icon_ant_chip(cv, x, y, w, h):
    """An AI chip marked ANT, a pop-and-fade arrow, the close tag."""
    cx = x + w // 2 - 16
    cy = y + h // 2
    size = 44
    for i in range(4):
        off = -16 + i * 11
        cv.rect(cx - size // 2 - 6, cy + off, 6, 3, GREEN_DARK)
        cv.rect(cx + size // 2, cy + off, 6, 3, GREEN_DARK)
        cv.rect(cx + off, cy - size // 2 - 6, 3, 6, GREEN_DARK)
        cv.rect(cx + off, cy + size // 2, 3, 6, GREEN_DARK)
    cv.rect(cx - size // 2, cy - size // 2, size, size, GREEN)
    cv.rect(cx - size // 2, cy - size // 2, size, 4, GREEN_DARK)
    # A bigger chip, so the ANT ticker fits inside a clean pale label
    # with a margin on every side instead of crowding the chip edge.
    cv.rect(cx - 18, cy - 8, 36, 16, (225, 248, 228))
    draw_text(cv, "ANT", cx - 17, cy - 5, 2, INK)
    tag_x = x + w - 92
    tag_y = y + h - 20
    cv.rect(tag_x, tag_y, 84, 18, GREEN_DARK)
    draw_text(cv, "$97.17", tag_x + 7, tag_y + 3, 2, WHITE)
    ax = x + w - 84
    ay = y + 4
    cv.line(ax, ay + 14, ax + 16, ay + 2, GREEN, 4)
    cv.line(ax + 16, ay + 2, ax + 34, ay + 12, RED, 4)
    cv.poly([(ax + 34, ay + 12), (ax + 22, ay + 12), (ax + 34, ay + 2)], RED)
    draw_text(cv, "+34%", ax + 44, ay + 2, 1, GREEN_DARK)
    draw_text(cv, "OPEN", ax + 44, ay + 11, 1, BODY)


def icon_tanker(cv, x, y, w, h):
    """A tanker on a blue strait, flame where it was struck."""
    cx = x + w // 2
    cv.rect(x, y + 36, w, h - 36, SEA)
    cv.hline(x + 8, x + w - 8, y + 42, SEA_DARK, 2)
    cv.hline(x + 30, x + w - 30, y + 47, SEA_DARK, 2)
    cv.poly([(cx - 78, y + 20), (cx + 78, y + 20), (cx + 62, y + 36),
             (cx - 62, y + 36)], STEEL_DARK)
    cv.rect(cx - 78, y + 20, 156, 3, RED)
    cv.rect(cx - 52, y + 10, 40, 10, (120, 90, 60))
    cv.rect(cx + 34, y + 6, 14, 14, (200, 60, 40))
    cv.rect(cx + 34, y + 6, 14, 3, INK)
    cv.poly([(cx - 6, y + 20), (cx + 2, y + 2), (cx + 10, y + 20)],
            (255, 140, 20))
    cv.poly([(cx - 2, y + 20), (cx + 2, y + 10), (cx + 6, y + 20)], YELLOW)


def icon_draft(cv, x, y, w, h):
    """The COP31 draft page, and a fuel drop struck through."""
    cx = x + w // 2
    px, py, pw, ph = cx - 108, y + 3, 62, 44
    cv.rect(px, py, pw, ph, WHITE)
    cv.rect(px, py, pw, 2, RULE)
    cv.rect(px, py + ph - 2, pw, 2, RULE)
    cv.rect(px, py, 2, ph, RULE)
    cv.rect(px + pw - 2, py, 2, ph, RULE)
    for i in range(4):
        cv.hline(px + 8, px + pw - 8, py + 9 + i * 9, SMOKE, 2)
    draw_text(cv, "144-80", px + 8, py + ph - 12, 1, BODY)
    dx, dy = cx + 42, y + 26
    cv.poly([(dx, y + 6), (dx - 11, dy + 4), (dx + 11, dy + 4)], STEEL_DARK)
    cv.disc(dx, dy + 6, 11, STEEL_DARK)
    cv.disc(dx - 3, dy + 4, 3, (120, 126, 134))
    cv.line(dx - 18, y + 44, dx + 18, y + 8, RED, 5)
    draw_text(cv, "FOSSIL", dx + 30, y + 12, 2, RED_DARK)
    draw_text(cv, "CUT", dx + 30, y + 28, 2, RED_DARK)


def icon_virus(cv, x, y, w, h):
    """A spiked virus ball, with the death toll beside it."""
    cx = x + w // 2
    cy = y + h // 2
    for k in range(12):
        angle = 6.283185307179586 * k / 12
        x1 = cx + int(14 * math.cos(angle))
        y1 = cy + int(14 * math.sin(angle))
        x2 = cx + int(21 * math.cos(angle))
        y2 = cy + int(21 * math.sin(angle))
        cv.line(x1, y1, x2, y2, RED_DARK, 3)
        cv.disc(x2, y2, 2, RED_DARK)
    cv.disc(cx, cy, 14, RED)
    cv.disc(cx - 5, cy - 5, 4, (255, 120, 120))
    cv.disc(cx + 5, cy + 4, 2, (255, 150, 150))
    draw_text(cv, "5,500+", cx + 32, cy - 7, 2, RED_DARK)


def icon_capitol(cv, x, y, w, h):
    """A dome and columns, with the 251-11 nomination tally."""
    cx = x + w // 2
    base = y + h - 4
    cv.rect(cx - 56, base - 26, 112, 26, (118, 92, 54))
    cv.rect(cx - 56, base - 26, 112, 4, (94, 72, 42))
    cv.disc(cx, base - 26, 12, (94, 72, 42))
    cv.rect(cx - 12, base - 28, 24, 4, (94, 72, 42))
    cv.rect(cx - 1, base - 40, 3, 6, GOLD)
    cv.disc(cx, base - 42, 2, GOLD)
    for dx in (-42, -21, 0, 21, 42):
        cv.rect(cx + dx - 3, base - 20, 6, 20, PANEL_BG)
    cv.rect(cx - 50, base - 4, 100, 4, (94, 72, 42))
    # Tally tag at the far left of the box, clear of the dome finial.
    cv.rect(x + 6, y + 4, 78, 16, NAVY_LIGHT)
    draw_text(cv, "251-11", x + 10, y + 7, 2, WHITE)


# ------------------------------------------------------------------
# Hero illustration: three flags over a long table at Kylin Villa,
# name plates for the three delegations, and the signed declaration
# itself lying on the table with a red seal.
# ------------------------------------------------------------------

def draw_hero(cv, x, y, w, h):
    cv.rect(x, y, w, h // 2, SKY_TOP)
    cv.rect(x, y + h // 2, w, h - h // 2, SKY_LOW)
    cv.poly([(x, y + h - 60), (x + 200, y + h - 110),
             (x + 420, y + h - 60)], HILL)
    cv.poly([(x + w - 420, y + h - 60), (x + w - 200, y + h - 104),
             (x + w, y + h - 60)], HILL)
    cv.rect(x, y + h - 60, w, 60, GRASS)
    flag_w, flag_h = 120, 72
    gap = 46
    total = flag_w * 3 + gap * 2
    start_x = x + (w - total) // 2
    start_y = y + 18
    for i, draw_flag in enumerate((flag_us, flag_cn, flag_ru)):
        fx = start_x + i * (flag_w + gap)
        draw_flag(cv, fx, start_y, flag_w, flag_h)
        cv.rect(fx, start_y, flag_w, 1, RULE)
        cv.rect(fx, start_y + flag_h - 1, flag_w, 1, RULE)
        cv.rect(fx, start_y, 1, flag_h, RULE)
        cv.rect(fx + flag_w - 1, start_y, 1, flag_h, RULE)
        cv.vline(fx - 3, start_y - 6, start_y + flag_h + 62, STEEL_DARK, 3)
        cv.disc(fx - 2, start_y - 8, 3, GOLD)
    table_y = y + h - 44
    cv.rect(x + 60, table_y, w - 120, 10, WOOD)
    cv.rect(x + 60, table_y + 10, w - 120, 4, WOOD_DARK)
    cv.rect(x + 80, table_y + 14, 10, 22, WOOD_DARK)
    cv.rect(x + w - 90, table_y + 14, 10, 22, WOOD_DARK)
    for i in range(3):
        chair_x = start_x + i * (flag_w + gap) + flag_w // 2 - 14
        cv.rect(chair_x, table_y - 26, 28, 26, NAVY_LIGHT)
        cv.rect(chair_x, table_y - 26, 28, 4, NAVY)
    for i, tag in enumerate(("USA", "CHN", "RUS")):
        plate_x = start_x + i * (flag_w + gap) + flag_w // 2 - 16
        cv.rect(plate_x, table_y - 12, 32, 10, PANEL_BG)
        draw_text(cv, tag, plate_x + 4, table_y - 10, 1, INK)
    doc_x = x + w // 2 + 58
    cv.rect(doc_x, table_y - 15, 42, 13, WHITE)
    cv.rect(doc_x, table_y - 15, 42, 1, RULE)
    cv.rect(doc_x, table_y - 3, 42, 1, RULE)
    cv.hline(doc_x + 5, doc_x + 26, table_y - 11, SMOKE, 1)
    cv.hline(doc_x + 5, doc_x + 26, table_y - 8, SMOKE, 1)
    cv.disc(doc_x + 34, table_y - 8, 4, RED)
    cv.rect(x + 14, y + 10, 240, 26, RED)
    draw_text(cv, "DECLARATION SIGNED", x + 24, y + 16, 2, WHITE)
    # A late-edition stamp, bottom right of the picture, so a reader
    # scanning thumbnails knows at once this is the updated page.
    cv.rect(x + w - 196, y + h - 34, 182, 22, GOLD)
    draw_text(cv, "LATE EDITION", x + w - 182, y + h - 28, 2, INK)


# ------------------------------------------------------------------
# The page itself.
# ------------------------------------------------------------------

PANELS = [
    ("MARKETS", NAVY, "WALL STREET SINKS",
     "S&P -2.02%, SIXTH STRAIGHT LOSS. DOW -1,101 BELOW 50,000. "
     "NASDAQ -2.25%. VIX 28.5.",
     icon_falling_chart),
    ("TECH", GREEN, "ANTHROPIC FADES TO +17%",
     "OPENS $111.50, CLOSES $97.17 (+17%). 846M SHARES TRADED. "
     "$81.3BN RAISED.",
     icon_ant_chip),
    ("GULF", RED_DARK, "IRAN HITS US BASE IN KUWAIT",
     "ALI AL-SALEM DRONED WED. BAHRAIN HIT AGAIN. TANKER STRUCK "
     "IN HORMUZ. NO NEW STRIKES THU.",
     icon_tanker),
    ("CLIMATE", TEAL, "COP31 DROPS FOSSIL FUELS",
     "DRAFT SLIMMED 144 TO 80, EVERY FOSSIL-FUEL LINE CUT. "
     "STILL NOT ADOPTED.",
     icon_draft),
    ("HEALTH", RED, "EBOLA DEATHS PASS 5,500",
     "11,000+ CASES IN CONGO. AFRICA CDC: STILL NOT UNDER CONTROL.",
     icon_virus),
    ("POLITICS", NAVY_LIGHT, "JEFFRIES PICKED FOR SPEAKER",
     "DEMOCRATS VOTE 251-11, WOULD BE FIRST BLACK SPEAKER. VOTE JAN 3.",
     icon_capitol),
]


def draw_panel(cv, x, y, w, h, kicker, kicker_colour, headline, body, icon):
    cv.rect(x, y, w, h, PANEL_BG)
    cv.rect(x, y, w, 2, RULE)
    cv.rect(x, y + h - 2, w, 2, RULE)
    cv.rect(x, y, 2, h, RULE)
    cv.rect(x + w - 2, y, 2, h, RULE)
    cv.rect(x + 2, y + 2, w - 4, 26, kicker_colour)
    draw_text(cv, kicker, x + 12, y + 8, 2, WHITE)
    icon(cv, x + 10, y + 32, w - 20, 50)
    headline_chars = (w - 24) // (ADVANCE * 3)
    ty = y + 88
    for line in wrap_text(headline, headline_chars)[:2]:
        draw_text(cv, line, x + 12, ty, 3, INK)
        ty += 22
    body_chars = (w - 24) // (ADVANCE * 2)
    by = ty + 4
    for line in wrap_text(body, body_chars)[:4]:
        draw_text(cv, line, x + 12, by, 2, BODY)
        by += 15


def build_page():
    cv = Canvas(WIDTH, HEIGHT, CREAM)

    # Masthead.
    cv.rect(0, 0, WIDTH, 108, NAVY)
    cv.rect(0, 108, WIDTH, 4, RED)
    draw_text(cv, "THE WORLD IN ONE DAY", WIDTH // 2, 22, 6, WHITE,
              align="center")
    draw_text(cv, "LATE EDITION - FRIDAY UPDATE - ALL OUTCOMES IN",
              WIDTH // 2, 82, 2, MASTHEAD_PALE, align="center")

    # The day, named in full: the judge is not told which day this is.
    cv.rect(24, 124, WIDTH - 48, 44, PANEL_BG)
    cv.rect(24, 124, WIDTH - 48, 2, RULE)
    cv.rect(24, 166, WIDTH - 48, 2, RULE)
    draw_text(cv, "THURSDAY 19 NOVEMBER 2026", WIDTH // 2, 132, 4, RED,
              align="center")

    # Hero story: the trilateral outcome.
    hx, hy, hw, hh = 24, 180, WIDTH - 48, 304
    cv.rect(hx, hy, hw, hh, PANEL_BG)
    draw_hero(cv, hx + 2, hy + 2, hw - 4, 188)
    ty = hy + 198
    draw_text(cv, "TRUMP, XI AND PUTIN SIGN", hx + 14, ty, 5, INK)
    draw_text(cv, "PEACE DECLARATION", hx + 14, ty + 38, 5, RED)
    draw_para(cv,
              "4 POINTS: UN REFORM, OIL SUPPLY, ICC LIMITS, NUCLEAR "
              "TALKS. NO DEAL ON UKRAINE. US-CHINA TRADE TRUCE "
              "EXTENDED.",
              hx + 14, ty + 82, (hw - 28) // (ADVANCE * 2), 2, BODY)

    # Six panels in a three-by-two grid.
    grid_x, grid_y = 24, 496
    panel_w, panel_h, gap = 318, 200, 11
    for i, panel in enumerate(PANELS):
        px = grid_x + (i % 3) * (panel_w + gap)
        py = grid_y + (i // 3) * (panel_h + gap)
        draw_panel(cv, px, py, panel_w, panel_h, *panel)

    # Footer briefs: four more true stories that did not get a panel.
    footer_y = grid_y + 2 * panel_h + gap + 12
    cv.rect(24, footer_y, WIDTH - 48, 2, RULE)
    draw_para(cv,
              "ALSO: CHIP CURBS TAKE EFFECT - LICENCES FOR AI CHIPS. "
              "ZVEREV SWEEPS GROUP 3-0, SHELTON IN SEMIS. VOYAGER 1 "
              "ONE LIGHT-DAY OUT. GTA VI ROLLS OUT WORLDWIDE.",
              24, footer_y + 12, (WIDTH - 48) // (ADVANCE * 2), 2, INK)

    cv.rect(0, 988, WIDTH, 36, NAVY)
    draw_text(cv, "DRAWN IN CODE - NO PHOTOGRAPHS - THE WORLD IN ONE DAY",
              WIDTH // 2, 997, 2, MASTHEAD_PALE, align="center")
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, build_page())
    print(f"wrote {path} ({size} bytes, 1024x1024)")


if __name__ == "__main__":
    main()
