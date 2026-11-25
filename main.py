"""The World in Six -- a one-page broadsheet poster for 24 November 2026.

Stdlib-only Python 3.13. Draws a 1024x1024 PNG that sums up the day's
world news in six panels under a masthead, and writes it to
$MAKEFUN_OUTPUT_DIR/entry.png (default /output). Fully deterministic:
same input bytes, same output bytes, every run.

Layout: ink masthead band, a 2x3 grid of story cards, each with a
coloured spine, a category chip, a big headline, a short summary and a
dateline, plus a source footer. Text is drawn with a hand-built 5x7
bitmap face, scaled up, so no imaging library is needed at runtime.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# --- palette: warm newsprint, deep ink, one accent per story ----------
PAPER = (244, 238, 225)
CARD = (255, 252, 244)
INK = (26, 33, 50)
SOFT = (74, 74, 66)
GOLD = (214, 163, 64)
RULE = (26, 33, 50)

ACCENTS = [
    (14, 122, 95),    # teal green   - tech
    (179, 55, 43),    # brick red    - conflict
    (199, 125, 26),   # amber        - energy
    (74, 93, 138),    # slate blue   - disaster
    (91, 58, 140),    # purple       - space
    (32, 97, 140),    # steel blue   - geopolitics
]

# --- the six stories of the day ---------------------------------------
STORIES = [
    {
        "tag": "TECH",
        "place": "SANTA CLARA, USA",
        "head": "HUANG IS BACK AT NVIDIA",
        "body": "Board reinstates Jensen Huang as CEO. Shares jump 31% in a day; S&P 500 up 4.7%.",
        "fact": "+31% SHARES IN A DAY",
    },
    {
        "tag": "CONFLICT",
        "place": "BENGHAZI, LIBYA",
        "head": "UKRAINE SINKS RUSSIAN WARSHIP",
        "body": "Seven naval drones sink the corvette Merkury at Benghazi port, Kyiv confirms.",
        "fact": "7 NAVAL DRONES",
    },
    {
        "tag": "ENERGY",
        "place": "STRAIT OF HORMUZ",
        "head": "THREE TANKERS HIT MINES",
        "body": "Iran says mines struck tankers in the Strait of Hormuz as the US blockade standoff deepens.",
        "fact": "3 TANKERS STRUCK",
    },
    {
        "tag": "DISASTER",
        "place": "BANTEN, INDONESIA",
        "head": "FACTORY FIRE KILLS 26",
        "body": "Blaze at a plant in Banten leaves 26 dead and dozens missing, officials say.",
        "fact": "DOZENS STILL MISSING",
    },
    {
        "tag": "SPACE",
        "place": "BEIJING, CHINA",
        "head": "PAKISTAN TO FLY ON TIANGONG",
        "body": "Zeeshan Ali set to be the first foreign astronaut aboard China's space station.",
        "fact": "1ST FOREIGN ASTRONAUT",
    },
    {
        "tag": "GEOPOLITICS",
        "place": "TALLINN, ESTONIA",
        "head": "RUSSIA WARNS ESTONIA OF WAR",
        "body": "Moscow says Tallinn's moves risk open war; NATO vows to defend space assets.",
        "fact": "NATO: WE WILL DEFEND SPACE",
    },
]

# --- 5x7 bitmap face, '#' is ink --------------------------------------
GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "%": ("#...#", "#..#.", "...#.", "..#..", ".#...", "#..#.", "#...#"),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    "&": (".###.", "#...#", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "*": (".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "....."),
    "=": (".....", ".....", ".###.", ".....", ".###.", ".....", "....."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
}


class Sheet:
    """A plain RGB canvas held as one bytearray."""

    def __init__(self, w, h, rgb):
        self.w = w
        self.h = h
        self.px = bytearray(rgb * (w * h))

    def paint(self, x, y, w, h, rgb):
        """Fill a rectangle, clipped to the canvas."""
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        r, g, b = rgb
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b

    def frame(self, x, y, w, h, rgb, thick=2):
        self.paint(x, y, w, thick, rgb)
        self.paint(x, y + h - thick, w, thick, rgb)
        self.paint(x, y, thick, h, rgb)
        self.paint(x + w - thick, y, thick, h, rgb)

    def glyph(self, x, y, ch, scale, rgb):
        rows = GLYPHS.get(ch)
        if rows is None:
            return
        for r, row in enumerate(rows):
            for c, bit in enumerate(row):
                if bit == "#":
                    self.paint(x + c * scale, y + r * scale, scale, scale, rgb)

    def text(self, x, y, s, scale, rgb):
        cx = x
        for ch in s:
            self.glyph(cx, y, ch, scale, rgb)
            cx += 6 * scale
        return cx

    def text_w(self, s, scale):
        if not s:
            return 0
        return len(s) * 6 * scale - scale


def wrap_lines(text, max_w, scale):
    """Greedy word wrap; returns a list of lines that fit max_w pixels."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        # width of a string at this scale
        w = len(trial) * 6 * scale - scale
        if w <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_masthead(cv):
    """The ink band across the top: title, date, six-colour motif."""
    x0, y0, w, h = 20, 20, 984, 118
    cv.paint(x0, y0, w, h, INK)
    cv.paint(x0, y0 + h - 4, w, 4, GOLD)
    # title, big
    cv.text(x0 + 24, y0 + 22, "THE WORLD IN SIX", 6, PAPER)
    # date line under it
    cv.text(x0 + 24, y0 + 82, "TUESDAY, 24 NOVEMBER 2026", 2, GOLD)
    # six accent squares on the right
    sx = x0 + w - 24 - 6 * 26
    for i, col in enumerate(ACCENTS):
        cv.paint(sx + i * 26, y0 + 26, 20, 20, col)
    tagline = "6 STORIES - ONE DAY"
    cv.text(x0 + w - 24 - cv.text_w(tagline, 2), y0 + 82, tagline, 2, PAPER)


def draw_card(cv, story, accent, x0, y0, w, h, num):
    """One story card: spine, chip, number, headline, body, dateline."""
    cv.paint(x0, y0, w, h, CARD)
    cv.frame(x0, y0, w, h, RULE, 2)
    cv.paint(x0, y0, 12, h, accent)
    # category chip
    tag = story["tag"]
    chip_w = cv.text_w(tag, 2) + 20
    cv.paint(x0 + 26, y0 + 16, chip_w, 26, accent)
    cv.text(x0 + 26 + 10, y0 + 21, tag, 2, CARD)
    # big story number, top right
    cv.text(x0 + w - 24 - cv.text_w(num, 3), y0 + 14, num, 3, accent)
    # headline, up to two lines
    lines = wrap_lines(story["head"], w - 52, 3)
    hy = y0 + 56
    for ln in lines[:2]:
        cv.text(x0 + 26, hy, ln, 3, INK)
        hy += 26
    # body, up to four lines (uppercased: the face is caps-only)
    body = wrap_lines(story["body"].upper(), w - 52, 2)
    by = hy + 10
    for ln in body[:4]:
        cv.text(x0 + 26, by, ln, 2, SOFT)
        by += 18
    # key-figure callout, in the accent colour
    cv.text(x0 + 26, y0 + h - 62, story["fact"], 2, accent)
    # dateline at the bottom
    cv.paint(x0 + 26, y0 + h - 40, w - 52, 2, accent)
    cv.text(x0 + 26, y0 + h - 30, story["place"], 2, accent)


def draw_footer(cv):
    line = "SOURCES: AP - REUTERS - BBC - THE GUARDIAN - KYIV INDEPENDENT"
    tw = cv.text_w(line, 2)
    cv.text((W - tw) // 2, 984, line, 2, SOFT)


def encode_png(w, h, rgb):
    """Minimal deterministic PNG encoder (truecolour, filter 0)."""
    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    for yy in range(h):
        raw.append(0)
        raw += rgb[yy * w * 3:(yy + 1) * w * 3]
    blob = b"\x89PNG\r\n\x1a\n"
    blob += chunk(b"IHDR", ihdr)
    blob += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    blob += chunk(b"IEND", b"")
    return blob


def build():
    cv = Sheet(W, H, PAPER)
    draw_masthead(cv)
    # 2 columns x 3 rows of cards
    gx, gy = 20, 156
    cw, chh, gap = 485, 262, 14
    for i, story in enumerate(STORIES):
        col = i % 2
        row = i // 2
        draw_card(
            cv, story, ACCENTS[i],
            gx + col * (cw + gap), gy + row * (chh + gap),
            cw, chh, "%02d" % (i + 1),
        )
    draw_footer(cv)
    return encode_png(W, H, cv.px)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    data = build()
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(data)
    print("wrote %s (%d bytes, %dx%d)" % (path, len(data), W, H))


if __name__ == "__main__":
    main()
