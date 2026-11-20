#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - late edition front page, drawn in pure code.

A single-file, standard-library-only program. It builds a 1024x1024
RGB picture pixel by pixel, then serialises it as a PNG with zlib.
Nothing here reads the clock or any random source, so every run of
the same code produces exactly the same file.
"""

import os
import struct
import zlib

WIDTH = 1024
HEIGHT = 1024

# Palette used across the whole page.
NAVY = (18, 34, 68)
NAVY_SOFT = (38, 58, 96)
PAPER = (250, 246, 233)
CREAM = (243, 236, 214)
INK = (24, 24, 28)
GREY = (96, 96, 104)
LIGHT_LINE = (203, 196, 176)
RED = (186, 28, 38)
RED_DARK = (140, 18, 28)
GOLD = (214, 164, 32)
GOLD_SOFT = (240, 205, 105)
SKY = (168, 205, 232)
SKY_DEEP = (120, 172, 216)
HILL_A = (96, 156, 92)
HILL_B = (64, 128, 72)
BROWN = (122, 82, 48)
BROWN_DARK = (88, 58, 32)
WHITE = (255, 255, 255)
BLACK = (10, 10, 12)
GREEN = (28, 138, 76)
GREEN_DARK = (18, 94, 54)
BLUE = (36, 84, 168)
WATER = (64, 132, 196)
ORANGE = (238, 118, 28)
PURPLE = (104, 62, 158)
TEAL = (18, 128, 128)
PINK = (206, 84, 120)


class Canvas:
    """A flat RGB pixel buffer with small drawing primitives."""

    def __init__(self, w, h, colour):
        self.w = w
        self.h = h
        self.px = bytearray(colour) * (w * h)

    def set(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = colour[0]
            self.px[i + 1] = colour[1]
            self.px[i + 2] = colour[2]

    def get(self, x, y):
        i = (y * self.w + x) * 3
        return (self.px[i], self.px[i + 1], self.px[i + 2])

    def rect(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(colour) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def frame(self, x, y, w, h, colour, thick=1):
        self.rect(x, y, w, thick, colour)
        self.rect(x, y + h - thick, w, thick, colour)
        self.rect(x, y, thick, h, colour)
        self.rect(x + w - thick, y, thick, h, colour)

    def line(self, x0, y0, x1, y1, colour, thick=1):
        # Bresenham walk, stamping a small square at each step so the
        # stroke stays solid at any angle.
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        half = thick // 2
        while True:
            self.rect(x0 - half, y0 - half, thick, thick, colour)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def dashed_line(self, x0, y0, x1, y1, colour, thick=2, dash=10, gap=7):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        period = dash + gap
        for s in range(steps + 1):
            if (s % period) >= dash:
                continue
            x = x0 + (x1 - x0) * s // steps
            y = y0 + (y1 - y0) * s // steps
            self.rect(x - thick // 2, y - thick // 2, thick, thick, colour)

    def circle(self, cx, cy, r, colour, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
                if fill:
                    if d2 <= r * r:
                        self.set(xx, yy, colour)
                else:
                    if (r - 1) * (r - 1) <= d2 <= r * r:
                        self.set(xx, yy, colour)

    def disc_ring(self, cx, cy, r_outer, r_inner, colour):
        for yy in range(cy - r_outer, cy + r_outer + 1):
            for xx in range(cx - r_outer, cx + r_outer + 1):
                d2 = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
                if r_inner * r_inner <= d2 <= r_outer * r_outer:
                    self.set(xx, yy, colour)

    def polygon(self, points, colour):
        # Scanline fill: for each row, collect edge crossings and
        # paint between them in pairs.
        ys = [p[1] for p in points]
        top = max(0, min(ys))
        bottom = min(self.h - 1, max(ys))
        n = len(points)
        for yy in range(top, bottom + 1):
            hits = []
            for i in range(n):
                x_a, y_a = points[i]
                x_b, y_b = points[(i + 1) % n]
                if y_a == y_b:
                    continue
                if (y_a <= yy < y_b) or (y_b <= yy < y_a):
                    x_hit = x_a + (yy - y_a) * (x_b - x_a) // (y_b - y_a)
                    hits.append(x_hit)
            hits.sort()
            for i in range(0, len(hits) - 1, 2):
                self.rect(hits[i], yy, hits[i + 1] - hits[i] + 1, 1, colour)


def write_png(canvas, path):
    """Serialise the canvas as a PNG file (filter 0 rows, zlib)."""
    raw = bytearray()
    stride = canvas.w * 3
    for yy in range(canvas.h):
        raw.append(0)
        start = yy * stride
        raw.extend(canvas.px[start:start + stride])
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag, payload):
        out = struct.pack(">I", len(payload)) + tag + payload
        out += struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        return out

    header = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", header)
    data += chunk(b"IDAT", compressed)
    data += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(data)
    return len(data)


# ------------------------------------------------------------------
# Hand-set 5x7 bitmap font. Each glyph is seven rows of five bits,
# written out as strings so the letterforms stay easy to audit.
# ------------------------------------------------------------------

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "01010", "00100", "00100", "00100", "01010", "10001"),
    "Y": ("10001", "01010", "00100", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
}


def text_width(text, scale):
    """Pixel width of a string: 5-wide glyphs plus one column gap."""
    if not text:
        return 0
    return len(text) * 6 * scale - scale


def draw_text(cv, x, y, text, scale, colour):
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[" "])
        for row_i, row in enumerate(glyph):
            for col_i, bit in enumerate(row):
                if bit == "1":
                    cv.rect(x + col_i * scale, y + row_i * scale,
                            scale, scale, colour)
        x += 6 * scale
    return x


def draw_centered(cv, cx, y, text, scale, colour):
    w = text_width(text, scale)
    draw_text(cv, cx - w // 2, y, text, scale, colour)
    return w


def wrap_text(text, scale, max_width):
    """Greedy word wrap measured in real glyph pixels."""
    lines = []
    current = ""
    for word in text.split(" "):
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_paragraph(cv, x, y, text, scale, colour, max_width,
                   line_gap=4, align="left", max_lines=None):
    lines = wrap_text(text, scale, max_width)
    if max_lines is not None:
        lines = lines[:max_lines]
    step = 7 * scale + line_gap
    for i, line in enumerate(lines):
        if align == "center":
            draw_centered(cv, x + max_width // 2, y + i * step,
                          line, scale, colour)
        else:
            draw_text(cv, x, y + i * step, line, scale, colour)
    return y + len(lines) * step


def tag_box(cv, x, y, text, scale, bg, fg, pad_x=6, pad_y=4):
    w = text_width(text, scale) + pad_x * 2
    h = 7 * scale + pad_y * 2
    cv.rect(x, y, w, h, bg)
    draw_text(cv, x + pad_x, y + pad_y, text, scale, fg)
    return w, h


# ------------------------------------------------------------------
# Scene: masthead, date banner and the hero picture.
# ------------------------------------------------------------------

def draw_flag_usa(cv, x, y, w, h):
    stripe = h // 7
    for i in range(7):
        col = RED if i % 2 == 0 else WHITE
        cv.rect(x, y + i * stripe, w, stripe, col)
    cv.rect(x, y + 6 * stripe, w, h - 6 * stripe,
            RED if 6 % 2 == 0 else WHITE)
    canton_w = w * 2 // 5
    canton_h = stripe * 4
    cv.rect(x, y, canton_w, canton_h, NAVY)
    for r in range(3):
        for c in range(4):
            cv.circle(x + 10 + c * 16, y + 9 + r * 12, 3, WHITE)
    cv.frame(x, y, w, h, INK, 2)


def draw_flag_china(cv, x, y, w, h):
    cv.rect(x, y, w, h, RED)
    # One large star plus a small arc of four, drawn as plus-stars.
    def star(cx, cy, r):
        cv.rect(cx - r, cy - r // 3, 2 * r + 1, 2 * (r // 3) + 1, GOLD_SOFT)
        cv.rect(cx - r // 3, cy - r, 2 * (r // 3) + 1, 2 * r + 1, GOLD_SOFT)
        cv.circle(cx, cy, r // 2, GOLD_SOFT)
    star(x + 24, y + 20, 11)
    for dx, dy in ((52, 10), (60, 24), (60, 40), (52, 54)):
        star(x + dx, y + dy, 5)
    cv.frame(x, y, w, h, INK, 2)


def draw_flag_russia(cv, x, y, w, h):
    band = h // 3
    cv.rect(x, y, w, band, WHITE)
    cv.rect(x, y + band, w, band, BLUE)
    cv.rect(x, y + 2 * band, w, h - 2 * band, RED)
    cv.frame(x, y, w, h, INK, 2)


def draw_hero(cv):
    # Picture frame.
    x0, y0, w, h = 24, 122, 976, 196
    cv.rect(x0, y0, w, h, SKY)
    cv.circle(x0 + 880, y0 + 34, 20, GOLD_SOFT)
    cv.circle(x0 + 880, y0 + 34, 14, GOLD)
    # Rolling hills behind the table.
    cv.polygon([(x0, y0 + 132), (x0 + 260, y0 + 92),
                (x0 + 520, y0 + 132), (x0, y0 + 196)], HILL_A)
    cv.polygon([(x0 + 430, y0 + 140), (x0 + 700, y0 + 96),
                (x0 + 976, y0 + 138), (x0 + 976, y0 + 196),
                (x0 + 430, y0 + 196)], HILL_B)
    cv.rect(x0, y0 + 168, w, 28, (52, 106, 60))

    # Three flags on poles.
    flag_y = y0 + 18
    flag_w, flag_h = 138, 76
    flag_xs = [x0 + 92, x0 + 419, x0 + 746]
    for fx in flag_xs:
        cv.rect(fx - 4, flag_y - 6, 4, 150, BROWN_DARK)
    draw_flag_usa(cv, flag_xs[0], flag_y, flag_w, flag_h)
    draw_flag_china(cv, flag_xs[1], flag_y, flag_w, flag_h)
    draw_flag_russia(cv, flag_xs[2], flag_y, flag_w, flag_h)

    # Long summit table.
    table_x, table_y, table_w = x0 + 70, y0 + 148, w - 140
    cv.rect(table_x, table_y, table_w, 14, BROWN)
    cv.rect(table_x + 16, table_y + 14, 12, 22, BROWN_DARK)
    cv.rect(table_x + table_w - 28, table_y + 14, 12, 22, BROWN_DARK)
    # Name plates: USA and RUS stand on the table behind its edge,
    # clear of the corner tags below; CHN sits on the grass in front
    # of the table centre, because the document hides the tabletop
    # at the middle seat.
    for cx, label in ((flag_xs[0] + flag_w // 2, "USA"),
                      (flag_xs[2] + flag_w // 2, "RUS")):
        plate_w = text_width(label, 2) + 14
        cv.rect(cx - plate_w // 2, table_y - 24, plate_w, 22, WHITE)
        cv.frame(cx - plate_w // 2, table_y - 24, plate_w, 22, INK, 1)
        draw_centered(cv, cx, table_y - 20, label, 2, INK)
    chn_cx = flag_xs[1] + flag_w // 2
    chn_w = text_width("CHN", 2) + 14
    cv.rect(chn_cx - chn_w // 2, table_y + 19, chn_w, 22, WHITE)
    cv.frame(chn_cx - chn_w // 2, table_y + 19, chn_w, 22, INK, 1)
    draw_centered(cv, chn_cx, table_y + 23, "CHN", 2, INK)

    # Signed document standing in the middle of the table.
    doc_x, doc_y, doc_w, doc_h = x0 + 408, y0 + 104, 160, 62
    cv.rect(doc_x, doc_y, doc_w, doc_h, WHITE)
    cv.frame(doc_x, doc_y, doc_w, doc_h, INK, 2)
    for i in range(3):
        cv.rect(doc_x + 12, doc_y + 10 + i * 11, 96, 4, GREY)
    cv.rect(doc_x + 12, doc_y + 43, 62, 4, GREY)
    cv.circle(doc_x + doc_w - 24, doc_y + doc_h - 18, 11, RED)
    cv.circle(doc_x + doc_w - 24, doc_y + doc_h - 18, 6, RED_DARK)
    draw_text(cv, doc_x + 10, doc_y - 14, "", 1, INK)

    # Red tag bottom-left and gold stamp bottom-right, inside frame.
    tag_box(cv, x0 + 10, y0 + h - 34, "DECLARATION SIGNED", 2,
            RED, WHITE, pad_x=7, pad_y=5)
    stamp_w = text_width("LATE EDITION", 2) + 16
    stamp_x = x0 + w - stamp_w - 10
    cv.rect(stamp_x, y0 + h - 36, stamp_w, 26, GOLD)
    cv.frame(stamp_x, y0 + h - 36, stamp_w, 26, NAVY, 2)
    draw_centered(cv, stamp_x + stamp_w // 2, y0 + h - 30,
                  "LATE EDITION", 2, NAVY)

    cv.frame(x0, y0, w, h, NAVY, 3)


def draw_masthead(cv):
    cv.rect(0, 0, WIDTH, 84, NAVY)
    cv.rect(0, 80, WIDTH, 4, GOLD)
    draw_centered(cv, WIDTH // 2, 10, "THE WORLD IN ONE DAY", 5, WHITE)
    draw_centered(cv, WIDTH // 2, 56,
                  "LATE EDITION - FRIDAY UPDATE - ALL OUTCOMES IN",
                  2, GOLD_SOFT)
    # Red date banner.
    cv.rect(0, 84, WIDTH, 30, RED)
    draw_centered(cv, WIDTH // 2, 89, "THURSDAY 19 NOVEMBER 2026",
                  3, WHITE)


# ------------------------------------------------------------------
# Six story panels. Each icon lives in a box 301 wide x 54 tall,
# drawn relative to the box origin passed in.
# ------------------------------------------------------------------

def icon_markets(cv, x, y):
    # Falling line chart smashing through a dashed 50,000 floor.
    cv.dashed_line(x + 8, y + 40, x + 292, y + 40, RED, thick=2)
    draw_text(cv, x + 10, y + 45, "50,000", 1, RED_DARK)
    pts = [(x + 16, y + 8), (x + 84, y + 16), (x + 140, y + 12),
           (x + 196, y + 30), (x + 252, y + 50)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], RED, thick=3)
    for px_, py_ in pts:
        cv.circle(px_, py_, 4, RED_DARK)
    cv.polygon([(x + 252, y + 42), (x + 266, y + 52),
                (x + 244, y + 54)], RED_DARK)


def icon_tech(cv, x, y):
    # A generous green chip so ANT reads cleanly, then a fade arrow.
    chip_x, chip_y, chip_w, chip_h = x + 18, y + 6, 108, 42
    for i in range(4):
        cv.rect(chip_x - 8, chip_y + 5 + i * 10, 8, 3, GREY)
        cv.rect(chip_x + chip_w, chip_y + 5 + i * 10, 8, 3, GREY)
    cv.rect(chip_x, chip_y, chip_w, chip_h, GREEN)
    cv.frame(chip_x, chip_y, chip_w, chip_h, GREEN_DARK, 2)
    draw_centered(cv, chip_x + chip_w // 2, chip_y + 11, "ANT", 3, WHITE)
    # Arrow pops up, then fades down to the close tag.
    cv.line(x + 142, y + 38, x + 178, y + 10, GREEN, thick=3)
    cv.line(x + 178, y + 10, x + 216, y + 30, ORANGE, thick=3)
    cv.polygon([(x + 216, y + 22), (x + 230, y + 34),
                (x + 208, y + 38)], ORANGE)
    tag_box(cv, x + 228, y + 8, "$97.17", 2, NAVY, GOLD_SOFT,
            pad_x=5, pad_y=3)


def icon_gulf(cv, x, y):
    # Tanker hull on water, with a flame over the deck.
    cv.rect(x, y + 38, 301, 16, WATER)
    for wx in range(10, 290, 36):
        cv.rect(x + wx, y + 44, 18, 3, SKY)
    hull = [(x + 58, y + 30), (x + 238, y + 30),
            (x + 222, y + 42), (x + 76, y + 42)]
    cv.polygon(hull, RED_DARK)
    cv.rect(x + 84, y + 20, 108, 10, GREY)
    cv.rect(x + 188, y + 12, 22, 18, NAVY_SOFT)
    cv.polygon([(x + 128, y + 2), (x + 140, y + 16),
                (x + 116, y + 16)], GOLD)
    cv.polygon([(x + 140, y + 4), (x + 150, y + 18),
                (x + 132, y + 18)], ORANGE)
    cv.circle(x + 138, y + 15, 5, RED)


def icon_climate(cv, x, y):
    # Draft page marked 144-80, next to a fuel drop crossed out.
    page_x, page_y = x + 34, y + 4
    cv.rect(page_x, page_y, 76, 48, WHITE)
    cv.frame(page_x, page_y, 76, 48, INK, 2)
    for i in range(3):
        cv.rect(page_x + 9, page_y + 8 + i * 9, 52, 3, GREY)
    tag_box(cv, page_x + 4, page_y + 32, "144-80", 1, GOLD, INK,
            pad_x=4, pad_y=2)
    # Fuel drop outline on the right, struck through in red.
    drop_cx, drop_cy = x + 196, y + 30
    cv.polygon([(drop_cx, y + 4), (drop_cx + 20, y + 30),
                (drop_cx + 14, y + 46), (drop_cx - 14, y + 46),
                (drop_cx - 20, y + 30)], INK)
    cv.polygon([(drop_cx, y + 14), (drop_cx + 11, y + 30),
                (drop_cx + 7, y + 40), (drop_cx - 7, y + 40),
                (drop_cx - 11, y + 30)], GOLD_SOFT)
    cv.line(x + 164, y + 48, x + 228, y + 8, RED, thick=4)
    draw_text(cv, x + 226, y + 22, "FOSSIL", 1, RED_DARK)
    draw_text(cv, x + 226, y + 32, "CUT", 1, RED_DARK)


def icon_health(cv, x, y):
    # Spiked virus ball, count written large beside it.
    cx, cy = x + 62, y + 27
    for dx, dy in ((0, -22), (16, -16), (22, 0), (16, 16), (0, 22),
                   (-16, 16), (-22, 0), (-16, -16)):
        cv.line(cx, cy, cx + dx, cy + dy, PURPLE, thick=3)
        cv.circle(cx + dx, cy + dy, 4, PURPLE)
    cv.circle(cx, cy, 17, PURPLE)
    cv.circle(cx - 6, cy - 5, 4, WHITE)
    cv.circle(cx + 7, cy + 6, 3, WHITE)
    draw_text(cv, x + 112, y + 12, "5,500+", 3, RED_DARK)
    draw_text(cv, x + 114, y + 38, "DEATHS", 1, GREY)


def icon_politics(cv, x, y):
    # Tally tag tucked top-left, Capitol dome clear in the centre.
    tag_box(cv, x + 4, y + 2, "251-11", 2, GOLD, INK, pad_x=5, pad_y=3)
    cx = x + 188
    cv.polygon([(cx - 34, y + 22), (cx, y + 2), (cx + 34, y + 22)],
               NAVY_SOFT)
    cv.rect(cx - 38, y + 22, 76, 5, NAVY)
    cv.rect(cx - 3, y - 2 + 2, 6, 8, NAVY)
    for i, dx in enumerate((-30, -15, 0, 15, 30)):
        cv.rect(cx + dx - 3, y + 30, 6, 16, NAVY_SOFT)
    cv.rect(cx - 44, y + 46, 88, 5, NAVY)



# ------------------------------------------------------------------
# Round 3 page: dark slate + amber front page. Date is the masthead,
# a figures strip follows, then numbered panels, an also-list with a
# dot-grid pin map and a how-sure legend, and a date-check footer.
# ------------------------------------------------------------------

SLATE = (31, 41, 55)
SLATE_DARK = (17, 24, 35)
AMBER = (232, 164, 28)
AMBER_SOFT = (246, 197, 92)
PAGE = (246, 244, 238)
PANEL_BG = (255, 255, 255)
BODY_INK = (52, 55, 62)
C_SHENZHEN = (150, 30, 40)
C_ICJ = (62, 52, 140)
C_MARKET = (160, 40, 20)
C_TECH = (18, 94, 54)
C_BERLIN = (36, 84, 168)
C_GULF = (120, 72, 10)
C_COP = (18, 110, 110)
C_EBOLA = (104, 40, 130)
C_FLORIDA = (30, 110, 160)
C_CHIP = (70, 70, 78)
C_GTA = (170, 60, 110)
C_SPACE = (40, 50, 130)
C_SPORT = (30, 120, 70)


def panel(cv, x, y, w, h, num, label, colour, headline, body, src,
          head_scale=2):
    cv.rect(x, y, w, h, PANEL_BG)
    cv.frame(x, y, w, h, SLATE, 2)
    cv.rect(x, y, w, 18, colour)
    cv.circle(x + 10, y + 9, 7, WHITE)
    draw_centered(cv, x + 10, y + 6, str(num), 1, colour)
    draw_text(cv, x + 21, y + 6, label, 1, WHITE)
    hy = y + 24
    hy = draw_paragraph(cv, x + 7, hy, headline, head_scale, INK,
                        w - 14, line_gap=2, max_lines=3)
    by = hy + 3
    draw_paragraph(cv, x + 7, by, body, 1, BODY_INK, w - 14,
                   line_gap=3, max_lines=12)
    draw_text(cv, x + 7, y + h - 12, src, 1, GREY)


def build_page():
    cv = Canvas(WIDTH, HEIGHT, PAGE)

    # Masthead: slate band, calendar box, date as largest text.
    cv.rect(0, 0, WIDTH, 116, SLATE_DARK)
    cv.rect(0, 112, WIDTH, 4, AMBER)
    cv.rect(14, 13, 88, 90, WHITE)
    cv.frame(14, 13, 88, 90, AMBER, 3)
    draw_centered(cv, 58, 19, "NOV", 2, SLATE)
    draw_centered(cv, 58, 40, "19", 5, C_SHENZHEN)
    draw_centered(cv, 58, 84, "THU 2026", 1, SLATE)
    draw_text(cv, 122, 18, "THURSDAY 19 NOVEMBER 2026", 5, WHITE)
    draw_text(cv, 124, 62, "THE WORLD IN ONE DAY", 3, AMBER_SOFT)
    draw_text(cv, 124, 92,
              "37 STORIES - 7 REGIONS - ALL FROM THIS ONE THURSDAY",
              2, WHITE)

    # Figures strip: amber band, 8 cells.
    cv.rect(0, 116, WIDTH, 52, AMBER)
    draw_text(cv, 14, 120, "THE DAY IN FIGURES", 1, SLATE_DARK)
    stats = [("9-6", "ICJ VOTE"), ("-1,101", "DOW POINTS"),
             ("-2.02%", "S+P 500"), ("+17%", "ANT CLOSE"),
             ("$81.3BN", "ANT RAISED"), ("5,500+", "EBOLA DEAD"),
             ("203,000", "JOBLESS CLAIMS"), ("$3,625", "GOLD LOW")]
    for i, (big, small) in enumerate(stats):
        cx = 12 + i * 126
        draw_text(cv, cx, 134, big, 2, SLATE_DARK)
        draw_text(cv, cx, 154, small, 1, SLATE_DARK)

    # Hero row: 3 panels.
    hy, hh = 176, 184
    hw = 325
    panel(cv, 12, hy, hw, hh, 1, "SHENZHEN - SUMMIT",
          C_SHENZHEN, "TRUMP XI PUTIN SIGN PEACE DECLARATION",
          "FIRST-EVER THREE-WAY SUMMIT, KYLIN VILLA, 1H45M. "
          "4 POINTS: UN REFORM, REFINED OIL, ICC LIMITS, NUCLEAR "
          "DIALOGUE. NO DEAL ON UKRAINE OR IRAN.",
          "REPORTED - AP / REUTERS / AFP", head_scale=3)
    panel(cv, 350, hy, hw, hh, 2, "THE HAGUE - COURT",
          C_ICJ, "WORLD COURT: MYANMAR DID COMMIT GENOCIDE",
          "ICJ RULES 9-6 ON ROHINGYA, PRESIDENT IWASAWA. CASE BY "
          "THE GAMBIA, 2019. ABOUT 10,000 KILLED IN 2017. FIRST "
          "STATE HELD TO GENOCIDE. REPARATIONS ORDERED.",
          "OFFICIAL - ICJ / AP / BBC", head_scale=3)
    panel(cv, 687, hy, hw, hh, 3, "NEW YORK - MARKETS",
          C_MARKET, "WALL STREET ROUT: S+P SIXTH LOSS IN A ROW",
          "S+P 7,175.83 -2.02%. DOW -1,101 TO 49,097, FIRST CLOSE "
          "UNDER 50,000 SINCE JUNE. NASDAQ -2.25%. VIX 28.5. "
          "HAWKISH FED MINUTES BEHIND IT.",
          "REPORTED - MARKET WIRES", head_scale=3)

    # Row 2: 5 panels.
    ry, rh, rw = 368, 158, 193
    panel(cv, 12, ry, rw, rh, 4, "NASDAQ - TECH", C_TECH,
          "ANTHROPIC CLOSES +17% ON DEBUT",
          "ANT OPENS $111.50 (+34%), CLOSES $97.17. PRICED $83. "
          "AMODEI SIBLINGS RANG THE BELL.", "REPORTED - NASDAQ / WIRES")
    panel(cv, 213, ry, rw, rh, 5, "BERLIN - UKRAINE", C_BERLIN,
          "30 HEADS BACK KYIV IN BERLIN",
          "MERZ MACRON BURNHAM HOST. ZELENSKYY, RUTTE, VON DER "
          "LEYEN, WITKOFF + KUSHNER THERE. EUR45BN LOAN ON TABLE.",
          "REPORTED - REUTERS / BBC")
    panel(cv, 414, ry, rw, rh, 6, "GULF - CONFLICT", C_GULF,
          "IRAN DRONES HIT US BASE IN KUWAIT",
          "ALI AL-SALEM HIT WED. TANKER STRUCK NEAR KHASAB IN "
          "HORMUZ. NO NEW STRIKES THU.", "REPORTED - AP / GULF NEWS")
    panel(cv, 615, ry, rw, rh, 7, "ANTALYA - CLIMATE", C_COP,
          "COP31 DRAFT CUTS FOSSIL FUELS",
          "DRAFT SLIMS 144 TO 80 LINES, EVERY FOSSIL-FUEL LINE "
          "OUT. DEAL STILL NOT DONE.", "REPORTED - UN NEWS / WIRES")
    panel(cv, 816, ry, rw, rh, 8, "CONGO - HEALTH", C_EBOLA,
          "EBOLA DEATHS PASS 5,500",
          "5,568 DEAD, 11,376 CASES. AFRICA CDC: STILL NOT UNDER "
          "CONTROL.", "OFFICIAL - AFRICA CDC / REUTERS")

    # Row 3: 5 panels.
    r3y = 534
    panel(cv, 12, r3y, rw, rh, 9, "FLORIDA - WEATHER", C_FLORIDA,
          "BROWARD SCHOOLS SHUT AFTER FLOODS",
          "SCHOOLS CLOSED THU AFTER 12-15 IN OF RAIN FLOODED "
          "HOLLYWOOD. I-95 SHUT, 300+ CALLS.", "OFFICIAL - NWS MIAMI / CNN")
    panel(cv, 213, r3y, rw, rh, 10, "WASHINGTON - TRADE", C_CHIP,
          "US CHIP CURBS START TODAY",
          "LICENCES NOW NEEDED FOR AI CHIPS TO SINGAPORE, "
          "MALAYSIA, INDONESIA, THAILAND, BRAZIL.", "OFFICIAL - US COMMERCE / WIRES")
    panel(cv, 414, r3y, rw, rh, 11, "GLOBAL - GAMES", C_GTA,
          "GTA VI ROLLS OUT WORLDWIDE",
          "BACK TO VICE CITY, LEONIDA. JASON + LUCIA LEAD. "
          "$79.99, 13 YEARS AFTER GTA V.", "REPORTED - XBOX / BBC")
    panel(cv, 615, r3y, rw, rh, 12, "SPACE - NASA", C_SPACE,
          "NASA CONFIRMS: VOYAGER ONE LIGHT-DAY OUT",
          "NASA CONFIRMS THU THE MILESTONE: 16.1BN MILES, RADIO "
          "NOW TAKES ABOUT 24H ONE WAY.", "OFFICIAL - NASA / JPL")
    panel(cv, 816, r3y, rw, rh, 13, "TURIN - TENNIS", C_SPORT,
          "ZVEREV SWEEPS GROUP 3-0",
          "BEATS FILS 6-4 7-6. NO SETS DROPPED. SHELTON JOINS "
          "HIM IN ATP FINALS SEMIS.", "REPORTED - ATP / WIRES")

    # Bottom band: also list (left) + pin map / legend (right).
    by, bh = 700, 218
    cv.rect(12, by, 688, bh, WHITE)
    cv.frame(12, by, 688, bh, SLATE, 2)
    draw_text(cv, 20, by + 7, "ALSO ON THURSDAY - 24 MORE STORIES",
              2, SLATE_DARK)
    also = [
        "14 GOLD $3,624.62, DOWN 2.68%, A 14-MONTH LOW",
        "15 US JOBLESS CLAIMS 203,000, ABOVE 197K FORECAST",
        "16 PHILLY FED FACTORY INDEX 6.3, FAR UNDER 20 FORECAST",
        "17 ASIA EARLY: TAIEX -3.73%, HANG SENG -1.89%",
        "18 KOSPI -1.60% EARLY; BRENT STEADIES NEAR $91.43",
        "19 HOUTHI MISSILE THREAT TO RIYADH: DEBRIS DAMAGE",
        "20 SENATE REPUBLICANS REJECT IRAN WAR-POWERS LIMIT",
        "21 UK PLEDGES 1,000 LONG-RANGE DRONES FOR UKRAINE",
        "22 GULF STATES, PAKISTAN, TURKEY PUSH TALKS TO STOP WAR",
        "23 TANKER STRUCK NEAR KHASAB, OMAN: CREW REPORTED SAFE",
        "24 ADNOC VESSEL ATTACK: 1 CREW MISSING, 11 INJURED",
        "25 BAHRAIN STOPS A 4TH ATTACK WAVE IN 6 DAYS",
        "26 ANT TRADED 846M SHARES, MOST-TRADED ON NASDAQ",
        "27 40 DELEGATIONS AT BERLIN COALITION TALKS",
        "28 TRUMP-XI EXTEND TRADE TRUCE, TERMS NOT DISCLOSED",
        "29 DECLARATION PLEDGES STATE CONSENT, ICC LIMITS",
        "30 EBOLA: HEALTH WORKERS STRIKE OVER UNPAID WAGES",
        "31 COP31: 21 ISSUES STILL OPEN AS SUMMIT NEARS END",
        "32 GTA VI: BBC ESTIMATES SALES TOP $2.3BN, A RECORD",
        "33 VOYAGER SIGNALS TAKE ABOUT 48H ROUND TRIP",
        "34 FED MINUTES: ALMOST ALL MEMBERS SAW MORE HIKES",
        "35 DECEMBER HIKE PRICED AT ABOUT 96% AFTER MINUTES",
        "36 S+P BROKE BELOW ITS 200-DAY AVERAGE ON THU",
        "37 ALL 11 S+P SECTORS FINISHED LOWER ON THU",
    ]
    for i, line in enumerate(also):
        col = i % 2
        row = i // 2
        lx = 20 + col * 344
        ly = by + 30 + row * 15
        draw_text(cv, lx, ly, line, 1, BODY_INK)

    # Right box: dot-grid pin map + how-sure legend.
    mx = 708
    cv.rect(mx, by, 304, bh, SLATE)
    draw_text(cv, mx + 10, by + 8, "WHERE IT HAPPENED", 2, AMBER_SOFT)
    pins = [(770, 782, "1"), (812, 762, "2"), (736, 762, "3"),
            (742, 786, "5"), (796, 796, "6"), (824, 782, "8"),
            (728, 806, "9"), (872, 806, "11"), (856, 762, "13")]
    for gy in range(by + 44, by + 128, 12):
        for gx in range(mx + 14, mx + 292, 12):
            cv.rect(gx, gy, 2, 2, (90, 104, 124))
    for px_, py_, n in pins:
        cv.circle(px_, py_, 8, AMBER)
        draw_centered(cv, px_, py_ - 3, n, 1, SLATE_DARK)
    draw_text(cv, mx + 10, by + 138, "HOW SURE ARE WE?", 2, WHITE)
    draw_text(cv, mx + 10, by + 162,
              "REPORTED: 2+ OUTLETS AGREE", 1, AMBER_SOFT)
    draw_text(cv, mx + 10, by + 178,
              "OFFICIAL: THE BODY ITSELF SAID IT", 1, AMBER_SOFT)
    draw_text(cv, mx + 10, by + 194,
              "CLAIM: ONE SIDE ONLY, LABELLED SO", 1, AMBER_SOFT)

    # Date-check footer.
    fy = 926
    cv.rect(0, fy, WIDTH, HEIGHT - fy, SLATE_DARK)
    cv.rect(0, fy, WIDTH, 4, AMBER)
    draw_text(cv, 14, fy + 10,
              "DATE CHECK: EVERY STORY ABOVE IS FROM THURSDAY "
              "19 NOVEMBER 2026", 2, AMBER_SOFT)
    draw_text(cv, 14, fy + 32,
              "LEFT OUT AS EARLIER NEWS: JEFFRIES NOMINATED WED 18. "
              "ANT PRICED WED 18.", 1, WHITE)
    draw_text(cv, 14, fy + 46,
              "HEGSETH VENEZUELA DEAL WED 18. EUR45BN LOAN PROPOSED "
              "WED 18.", 1, WHITE)
    draw_text(cv, 14, fy + 60,
              "LEFT OUT AS UNVERIFIED: NORTH KOREA MISSILE CLAIM. "
              "CRIMEAN BRIDGE CLAIM.", 1, WHITE)
    draw_text(cv, 14, fy + 74,
              "NOT YET HAPPENED: COP31 FINAL DEAL, DUE FRI 20. "
              "HOUSE SPEAKER VOTE, JAN 3.", 1, WHITE)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(build_page(), path)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
