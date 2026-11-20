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


PANELS = [
    ("MARKETS", RED, "WALL STREET SINKS",
     "S&P -2.02%, SIXTH STRAIGHT LOSS. DOW -1,101 BELOW 50,000. "
     "NASDAQ -2.25%. VIX 28.5.", icon_markets),
    ("TECH", GREEN_DARK, "ANTHROPIC FADES TO +17%",
     "OPENS $111.50, CLOSES $97.17 (+17%). 846M SHARES TRADED. "
     "$81.3BN RAISED.", icon_tech),
    ("GULF", BLUE, "IRAN HITS US BASE IN KUWAIT",
     "ALI AL-SALEM DRONED WED. BAHRAIN HIT AGAIN. TANKER STRUCK "
     "IN HORMUZ. NO NEW STRIKES THU.", icon_gulf),
    ("CLIMATE", TEAL, "COP31 DROPS FOSSIL FUELS",
     "DRAFT SLIMMED 144 TO 80, EVERY FOSSIL-FUEL LINE CUT. "
     "STILL NOT ADOPTED.", icon_climate),
    ("HEALTH", PURPLE, "EBOLA DEATHS PASS 5,500",
     "11,000+ CASES IN CONGO. AFRICA CDC: STILL NOT UNDER "
     "CONTROL.", icon_health),
    ("POLITICS", NAVY_SOFT, "JEFFRIES PICKED FOR SPEAKER",
     "DEMOCRATS VOTE 251-11, WOULD BE FIRST BLACK SPEAKER. "
     "VOTE JAN 3.", icon_politics),
]


def draw_panel(cv, px, py, pw, ph, panel):
    kicker, colour, headline, body, icon_fn = panel
    cv.rect(px, py, pw, ph, WHITE)
    cv.frame(px, py, pw, ph, NAVY, 2)
    cv.rect(px, py, pw, 24, colour)
    draw_text(cv, px + 9, py + 5, kicker, 2, WHITE)
    icon_fn(cv, px + 8, py + 30)
    head_y = py + 92
    head_end = draw_paragraph(cv, px + 9, head_y, headline, 2, INK,
                              pw - 18, line_gap=3, max_lines=2)
    body_y = max(head_end + 2, py + 126)
    draw_paragraph(cv, px + 9, body_y, body, 2, (52, 52, 58),
                   pw - 18, line_gap=3, max_lines=4)


def build_page():
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    draw_masthead(cv)
    draw_hero(cv)
    # Hero headline and standfirst under the picture.
    draw_centered(cv, WIDTH // 2, 330, "TRUMP, XI AND PUTIN SIGN", 5, INK)
    draw_centered(cv, WIDTH // 2, 374, "PEACE DECLARATION", 5, RED_DARK)
    draw_paragraph(
        cv, 62, 420,
        "4 POINTS: UN REFORM, OIL SUPPLY, ICC LIMITS, NUCLEAR "
        "TALKS. NO DEAL ON UKRAINE. US-CHINA TRADE TRUCE EXTENDED.",
        2, (52, 52, 58), 900, line_gap=4, align="center", max_lines=2)
    cv.rect(24, 456, 976, 3, GOLD)
    # Six panels, three across and two down.
    pw, ph, gap = 317, 208, 12
    for idx, panel in enumerate(PANELS):
        col = idx % 3
        row = idx // 3
        px = 24 + col * (pw + gap)
        py = 466 + row * (ph + 8)
        draw_panel(cv, px, py, pw, ph, panel)
    # Footer briefs, wrapped and centred.
    draw_paragraph(
        cv, 32, 898,
        "ALSO: CHIP CURBS TAKE EFFECT - LICENCES FOR AI CHIPS. "
        "ZVEREV SWEEPS GROUP 3-0, SHELTON IN SEMIS. VOYAGER 1 ONE "
        "LIGHT-DAY OUT. GTA VI ROLLS OUT WORLDWIDE.",
        2, INK, 960, line_gap=4, align="center", max_lines=3)
    # Bottom credit bar.
    cv.rect(0, 968, WIDTH, 56, NAVY)
    cv.rect(0, 968, WIDTH, 4, GOLD)
    draw_centered(cv, WIDTH // 2, 988,
                  "DRAWN IN CODE - NO PHOTOGRAPHS - THE WORLD IN ONE DAY",
                  2, WHITE)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(build_page(), path)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
