#!/usr/bin/env python3
"""news-image-20261119: sum up Thursday 19 November 2026 in one image.

Renders a dark-slate newspaper front page for a single day of world news
using nothing but the Python standard library: a hand-rolled PNG encoder
(zlib + struct) and a hand-drawn 5x7 bitmap font. No files are read, no
network is used, and the output is byte-for-byte deterministic.
"""

import os
import struct
import zlib

W = 1024
H = 1024

# Palette: deep slate paper, amber accents, off-white ink.
BG = (23, 27, 35)
PANEL = (33, 39, 51)
PANEL_LINE = (72, 82, 100)
INK = (238, 235, 226)
MUTE = (168, 176, 189)
AMBER = (242, 178, 44)
RED = (228, 102, 84)
GREEN = (102, 199, 122)

# 5x7 bitmap font. Each glyph is seven row values; in each row the five
# bits are the five pixels, most significant bit on the left.
FONT = {
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (15, 16, 16, 16, 16, 16, 15),
    "D": (28, 18, 17, 17, 17, 18, 28),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (15, 16, 16, 23, 17, 17, 14),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (31, 4, 4, 4, 4, 4, 31),
    "J": (7, 1, 1, 1, 1, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 27, 17),
    "X": (17, 10, 4, 4, 4, 10, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 6, 4, 12, 16, 31),
    "0": (14, 17, 19, 21, 25, 17, 14),
    "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 2, 4, 8, 31),
    "3": (30, 1, 1, 14, 1, 1, 30),
    "4": (2, 6, 10, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (14, 16, 16, 30, 17, 17, 14),
    "7": (31, 1, 2, 4, 4, 4, 4),
    "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 1, 14),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 12, 12),
    ",": (0, 0, 0, 0, 12, 12, 8),
    ":": (0, 12, 12, 0, 12, 12, 0),
    ";": (0, 12, 12, 0, 12, 12, 8),
    "'": (12, 12, 8, 0, 0, 0, 0),
    "-": (0, 0, 0, 31, 0, 0, 0),
    "+": (0, 4, 4, 31, 4, 4, 0),
    "%": (25, 26, 1, 2, 4, 8, 19),
    "$": (4, 15, 20, 14, 5, 30, 4),
    "/": (1, 1, 2, 4, 8, 16, 16),
    "(": (2, 4, 8, 8, 8, 4, 2),
    ")": (8, 4, 2, 2, 2, 4, 8),
    "!": (4, 4, 4, 4, 4, 0, 4),
    "?": (14, 17, 1, 2, 4, 0, 4),
    "&": (12, 18, 20, 8, 21, 18, 13),
    "·": (0, 0, 0, 12, 12, 0, 0),
}

FB = bytearray(W * H * 3)


def fill_rect(x, y, w, h, color):
    """Fill an axis-aligned rectangle in the framebuffer."""
    r, g, b = color
    for yy in range(y, y + h):
        if yy < 0 or yy >= H:
            continue
        base = yy * W * 3
        for xx in range(x, x + w):
            if xx < 0 or xx >= W:
                continue
            i = base + xx * 3
            FB[i] = r
            FB[i + 1] = g
            FB[i + 2] = b


def frame_rect(x, y, w, h, color, thick):
    fill_rect(x, y, w, thick, color)
    fill_rect(x, y + h - thick, w, thick, color)
    fill_rect(x, y, thick, h, color)
    fill_rect(x + w - thick, y, thick, h, color)


def text_width(s, scale):
    if not s:
        return 0
    return len(s) * 6 * scale - scale


def draw_text(x, y, s, scale, color):
    """Draw one line of text with the bitmap font; returns its width."""
    s = s.upper()
    cx = x
    for ch in s:
        glyph = FONT.get(ch, FONT["?"])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits & (1 << (4 - col)):
                    fill_rect(cx + col * scale, y + row * scale,
                              scale, scale, color)
        cx += 6 * scale
    return cx - scale - x


def draw_centered(y, s, scale, color, x0=0, x1=W):
    w = text_width(s, scale)
    draw_text(x0 + (x1 - x0 - w) // 2, y, s, scale, color)


def wrap_text(s, max_chars):
    """Greedy word wrap into lines of at most max_chars characters."""
    lines = []
    cur = ""
    for word in s.split():
        trial = word if not cur else cur + " " + word
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(x, y, lines, scale, color, leading):
    for i, line in enumerate(lines):
        draw_text(x, y + i * leading, line, scale, color)
    return y + len(lines) * leading


def save_png(path):
    """Write the framebuffer as a PNG using only zlib and struct."""
    raw = bytearray()
    row_bytes = W * 3
    for yy in range(H):
        raw.append(0)
        raw += FB[yy * row_bytes:(yy + 1) * row_bytes]
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


def panel_shell(x, y, w, h):
    fill_rect(x, y, w, h, PANEL)
    frame_rect(x, y, w, h, PANEL_LINE, 2)
    fill_rect(x, y, w, 4, AMBER)


def hero_panel(x, y, w, h, num, place, tag, head, body):
    """Large panel: big number, scale-3 headline, scale-2 body."""
    panel_shell(x, y, w, h)
    tx = x + 12
    draw_text(tx, y + 10, str(num), 3, AMBER)
    draw_text(tx + text_width(str(num), 3) + 10, y + 14, place, 2, INK)
    draw_text(tx, y + 36, tag, 1, AMBER)
    head_lines = wrap_text(head, (w - 24) // 18)
    hy = draw_block(tx, y + 50, head_lines, 3, INK, 25)
    max_body = (y + h - 8 - (hy + 6)) // 16
    body_lines = wrap_text(body, (w - 24) // 12)[:max_body]
    draw_block(tx, hy + 6, body_lines, 2, MUTE, 16)


def small_panel(x, y, w, h, num, place, tag, head, body):
    """Compact panel: scale-2 headline, scale-1 body."""
    panel_shell(x, y, w, h)
    tx = x + 8
    draw_text(tx, y + 8, str(num), 2, AMBER)
    draw_text(tx + text_width(str(num), 2) + 7, y + 11, place, 1, INK)
    draw_text(tx, y + 26, tag, 1, AMBER)
    head_lines = wrap_text(head, (w - 16) // 12)
    hy = draw_block(tx, y + 37, head_lines, 2, INK, 17)
    max_body = (y + h - 6 - (hy + 4)) // 9
    body_lines = wrap_text(body, (w - 16) // 6)[:max_body]
    draw_block(tx, hy + 4, body_lines, 1, MUTE, 9)


FIGURES = [
    ("9-6", "WORLD COURT VOTE ON MYANMAR", INK),
    ("-1,101", "DOW POINTS LOST ON THURSDAY", RED),
    ("-2.02%", "S&P 500: SIXTH LOSS IN A ROW", RED),
    ("+17%", "ANTHROPIC FIRST-DAY CLOSE", GREEN),
    ("$81.3BN", "RAISED IN THE ANT DEBUT", INK),
    ("5,500+", "EBOLA DEATHS IN DR CONGO", INK),
    ("203,000", "US JOBLESS CLAIMS FILED", INK),
    ("$3,625", "GOLD CLOSE: 14-MONTH LOW", AMBER),
]

HEROES = [
    (1, "SHENZHEN, CHINA", "REPORTED · AP / REUTERS",
     "TRUMP, XI, PUTIN SIGN PEACE PACT",
     "First three-way summit, Kylin Villa, 1h45m. Points: UN reform, "
     "stable energy, ICC-court limits, nuclear-risk dialogue."),
    (2, "THE HAGUE", "OFFICIAL · ICJ / AP",
     "WORLD COURT RULES GENOCIDE",
     "9-6 ruling: Myanmar did genocide of the Rohingya. Gambia case "
     "(2019), Pres. Iwasawa. First state ever held responsible. "
     "Reparations due."),
    (3, "NEW YORK", "REPORTED · REUTERS",
     "DOW LOSES 1,101 IN WALL ST ROUT",
     "S&P -2.02% to 7,175.83, 6th loss in a row. Dow -1,101.11 to "
     "49,097.06: first close under 50,000 since June. Nasdaq -2.25%. "
     "VIX 28.5."),
]

SMALLS = [
    (4, "NASDAQ", "REPORTED · BLOOMBERG",
     "ANTHROPIC +17% AT DEBUT",
     "ANT opens $111.50 (+34%), closes $97.17. $81.34bn raised; 846m "
     "shares traded, most on Nasdaq. Dario and Daniela Amodei ring "
     "the bell."),
    (5, "BERLIN", "REPORTED · REUTERS",
     "30 LEADERS BACK UKRAINE",
     "Coalition of the Willing: 40 delegations, hosts Merz, Macron, "
     "Burnham. Zelenskyy, Rutte, von der Leyen; US envoys Witkoff, "
     "Kushner. EU loan plan on table."),
    (6, "THE GULF", "REPORTED · REUTERS / AP",
     "IRAN DRONES HIT KUWAIT",
     "Drones at Ali Al-Salem base. Bahrain stops 4th attack wave in "
     "6 days. Tanker struck near Khasab, Hormuz. ADNOC vessel: 1 "
     "missing, 11 injured. No new strikes Thu."),
    (7, "ANTALYA", "REPORTED · AFP",
     "FOSSIL FUELS LEAVE DRAFT",
     "COP31 Thu draft drops every fossil-fuel line, cut 144 to 80 "
     "paragraphs. 21 issues still open. Summit deadlocked; closes "
     "Fri 20 Nov."),
    (8, "DR CONGO", "REPORTED · AFRICA CDC",
     "EBOLA DEATHS TOP 5,500",
     "DR Congo: 5,568 dead, 11,376 cases. Africa CDC says outbreak "
     "still not under control. Health workers strike over unpaid "
     "wages."),
    (9, "FLORIDA", "REPORTED · AP",
     "SCHOOLS SHUT IN BROWARD",
     "Thu closures after 12-15 in rain floods Hollywood, Fla. 300+ "
     "rescue calls. I-95 and Turnpike shut. Temple Sinai roof "
     "collapses."),
    (10, "WASHINGTON", "OFFICIAL · US GOVT",
     "AI CHIP CURBS NOW LIVE",
     "US licences now needed to ship advanced AI chips to Singapore, "
     "Malaysia, Indonesia, Thailand and Brazil. 12m TPP compute "
     "rule."),
    (11, "WORLDWIDE", "REPORTED · BBC",
     "GTA VI IS FINALLY OUT",
     "Worldwide after 13 years: Vice City, Leonida. Jason Duval and "
     "Lucia Caminos lead. $79.99 on PS5, Xbox. BBC: sales may top "
     "$2.3bn."),
    (12, "DEEP SPACE", "OFFICIAL · NASA",
     "VOYAGER ONE LIGHT-DAY OUT",
     "NASA confirms Thu: probe is 16.1bn miles from Earth. Radio "
     "signals take 24h one way, 48h for a round trip."),
    (13, "TURIN", "REPORTED · ATP",
     "ZVEREV SWEEPS TO SEMIS",
     "Beats Arthur Fils 6-4, 7-6(8-6) Thu night in Turin, a 3-0 "
     "group sweep. Shelton (2-1) also reaches ATP Finals semis."),
]

ALSO = [
    "GOLD $3,624.62, -2.68%, 14-MONTH LOW",
    "JOBLESS CLAIMS 203,000 VS 197,000 SEEN",
    "PHILLY FED 6.3 VS ABOUT 20 FORECAST",
    "TAIEX -3.73% HANG SENG -1.89% KOSPI -1.60%",
    "BRENT $91.43 AFTER WED $91.95 SETTLE",
    "HOUTHI THREAT AT RIYADH: DEBRIS DAMAGE",
    "SENATE GOP BLOCKS IRAN WAR-POWERS LIMIT",
    "FED MINUTES HAWKISH; DEC HIKE 96% PRICED",
    "ANT GREY MARKET WAS $98 BEFORE OPEN",
    "1-TO-1S: TRUMP-XI 1H, TRUMP-PUTIN 42 MIN",
    "TRILATERAL BEGAN ABOUT 2 HOURS LATE",
    "NEW START LAPSED FEB 2026, CAPS GONE",
    "EBOLA: $1.3BN OF $2.9BN PLEDGES RELEASED",
    "DECLARATION OMITS UKRAINE AND IRAN",
    "DECLARATION: MORE REFINED OIL SUPPLY",
    "DECLARATION: IMMUNITIES PARAMOUNT",
    "GTA VI UNLOCKS FROM NEW ZEALAND FIRST",
    "S&P STREAK LONGEST SINCE APRIL 2024",
    "NASDAQ-100 15.4% BELOW OCT 6 HIGH",
    "ANT RANGE: HIGH $115.10, LOW $92.72",
    "UK PLEDGES 1,000 LONG-RANGE STRIKE DRONES",
    "FT LAUDERDALE 5.72 IN TOPS 1959 RECORD",
    "ALL 11 S&P SECTORS CLOSE LOWER",
    "S&P DROPS BELOW 200-DAY AVERAGE",
]

LEGEND = [
    "REPORTED - NAMED NEWS SOURCES AGREE",
    "OFFICIAL - SAID BY THE BODY ITSELF",
    "CLAIM - ONE SIDE SAYS SO; UNCHECKED",
]

DATE_CHECK = (
    "LEFT OUT AS EARLIER NEWS (WED 18): ANTHROPIC $83 PRICING, "
    "JEFFRIES VOTE 251-11, HEGSETH VENEZUELA DEAL, EU LOAN PLAN, "
    "VOYAGER CROSSING. NOT YET: COP31 ENDS FRI 20. UNVERIFIED, LEFT "
    "OUT: N. KOREA MISSILE AND CRIMEAN BRIDGE CLAIMS."
)


def render():
    fill_rect(0, 0, W, H, BG)

    # Top strip and rule.
    draw_centered(10, "EVERY STORY FROM ONE DAY · 37 STORIES · 7 REGIONS",
                  2, AMBER)
    fill_rect(14, 30, W - 28, 2, AMBER)

    # Masthead: the date is the biggest thing on the page.
    draw_text(14, 38, "THURSDAY", 11, INK)
    draw_text(14, 121, "19 NOVEMBER 2026", 7, INK)
    frame_rect(862, 38, 148, 132, AMBER, 3)
    draw_centered(46, "19", 11, AMBER, 862, 1010)
    draw_centered(128, "NOV 2026", 2, INK, 862, 1010)
    draw_centered(146, "THU", 2, AMBER, 862, 1010)

    # Sub-headline: the day's top stories in one breath.
    draw_centered(180, "SHENZHEN SUMMIT SIGNS A PEACE DECLARATION · "
                       "WORLD COURT RULES GENOCIDE IN MYANMAR", 2, AMBER)
    draw_centered(198, "WALL STREET ROUT DEEPENS · ANTHROPIC SOARS ON "
                       "DEBUT · EBOLA DEATHS PASS 5,500", 2, AMBER)

    # The day in figures: eight big numbers, four across, two rows.
    draw_text(14, 224, "THE DAY IN FIGURES", 2, AMBER)
    for i, (num, label, color) in enumerate(FIGURES):
        cx = 14 + (i % 4) * 251
        cy = 250 + (i // 4) * 62
        draw_text(cx, cy, num, 5, color)
        draw_block(cx, cy + 40, wrap_text(label, 40), 1, MUTE, 9)

    # Hero row: the three biggest stories.
    for i, args in enumerate(HEROES):
        hero_panel(14 + i * 335, 368, 325, 214, *args)

    # Two rows of five smaller panels.
    for row in range(2):
        for col in range(5):
            args = SMALLS[row * 5 + col]
            small_panel(14 + col * 201, 590 + row * 150, 192, 142, *args)

    # Bottom band, left: how sure are we, and the date check.
    draw_text(14, 892, "HOW SURE ARE WE?", 2, AMBER)
    draw_block(14, 914, LEGEND, 1, MUTE, 10)
    draw_text(14, 948, "DATE CHECK", 2, AMBER)
    draw_block(14, 970, wrap_text(DATE_CHECK, 64), 1, MUTE, 10)

    # Bottom band, right: also on Thursday, stories 14 to 37.
    draw_text(412, 892, "ALSO ON THURSDAY - 24 MORE STORIES", 2, AMBER)
    for i, item in enumerate(ALSO):
        col_x = 412 if i < 12 else 718
        row_y = 914 + (i % 12) * 8
        draw_text(col_x, row_y, "%d %s" % (14 + i, item), 1, INK)

    draw_centered(1013, "ONE DAY · ONE PAGE · EVERY FACT CROSS-CHECKED "
                        "AGAINST NAMED SOURCES", 1, MUTE)


def main():
    render()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    save_png(os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
