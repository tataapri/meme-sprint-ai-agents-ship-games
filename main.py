#!/usr/bin/env python3
"""Meme Sprint: AI Agents Ship Games.

A pure-stdlib program that draws one meme about AI agents building games
and writes it to /output/entry.png.

The meme: two panels.
  Panel 1 - the agent, proudly: "I BUILT YOUR GAME IN 30 SECONDS"
  Panel 2 - the game itself: "NO WIN CONDITION / 47 PLUGINS /
  FINAL BOSS: A DUCK" (a crowned duck with a boss HP bar).

Everything is drawn by hand: a 5x7 bitmap font embedded below, simple bold
shapes, and a PNG encoder written with zlib + struct. No third-party
packages, no network, no system fonts.
"""

import math
import os
import struct
import zlib

# ---------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is 7 rows of 5 pixels ('#' = on, '.' = off).
# ---------------------------------------------------------------------------
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    ":": (".....", "..#..", ".....", ".....", ".....", "..#..", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".....", "..#.."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
}

# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------
W, H = 1024, 1024
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 210, 63)      # meme yellow
NAVY = (20, 33, 61)          # dark "game screen"
STEEL = (154, 165, 177)      # robot body
LIGHT = (192, 192, 192)      # robot head
DARKGREY = (70, 76, 84)
SCREEN = (16, 24, 40)        # laptop screen
GREEN = (57, 255, 120)       # code lines on the laptop
ORANGE = (255, 140, 0)       # duck beak / feet
RED = (220, 38, 38)          # boss HP bar
DUCKY = (255, 213, 74)       # duck body
DUCKWING = (232, 178, 32)

canvas = bytearray(W * H * 3)


def set_px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        canvas[i], canvas[i + 1], canvas[i + 2] = color


def fill_rect(x, y, w, h, color):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            canvas[i], canvas[i + 1], canvas[i + 2] = color


def fill_circle(cx, cy, r, color):
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(r * r - dy * dy))
        fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)


def fill_ellipse(cx, cy, rx, ry, color):
    for dy in range(-ry, ry + 1):
        dx = int(rx * math.sqrt(max(0.0, 1.0 - (dy * dy) / float(ry * ry))))
        fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)


def fill_triangle(p1, p2, p3, color):
    (x1, y1), (x2, y2), (x3, y3) = p1, p2, p3
    ymin, ymax = min(y1, y2, y3), max(y1, y2, y3)
    for y in range(ymin, ymax + 1):
        xs = []
        for (ax, ay), (bx, by) in ((p1, p2), (p2, p3), (p3, p1)):
            if ay == by:
                continue
            if min(ay, by) <= y < max(ay, by):
                xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
        if len(xs) >= 2:
            xa, xb = int(min(xs)), int(max(xs))
            fill_rect(xa, y, xb - xa + 1, 1, color)


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text(text, cx, y, scale, color):
    """Draw text centred on cx, top edge at y."""
    x = cx - text_width(text, scale) // 2
    for ch in text:
        glyph = FONT.get(ch.upper(), FONT[" "])
        for row in range(7):
            for col in range(5):
                if glyph[row][col] == "#":
                    fill_rect(x + col * scale, y + row * scale,
                              scale, scale, color)
        x += 6 * scale


# ---------------------------------------------------------------------------
# Panel 1: the agent (yellow background)
# ---------------------------------------------------------------------------
fill_rect(0, 0, W, 512, YELLOW)

draw_text("THE AGENT:", 512, 30, 4, BLACK)
draw_text("I BUILT YOUR GAME", 512, 82, 8, BLACK)
draw_text("IN 30 SECONDS", 512, 150, 8, BLACK)

# Robot: head with antenna, eyes, smile; body; laptop with code.
# Antenna
fill_rect(508, 224, 8, 26, BLACK)
fill_circle(512, 216, 12, RED)
# Head
fill_rect(412, 250, 200, 110, LIGHT)
fill_rect(412, 250, 200, 110, BLACK)  # placeholder overwritten below
fill_rect(418, 256, 188, 98, LIGHT)
# Head side bolts
fill_rect(400, 292, 12, 24, DARKGREY)
fill_rect(612, 292, 12, 24, DARKGREY)
# Eyes (white with black pupils)
fill_rect(448, 282, 44, 44, WHITE)
fill_rect(532, 282, 44, 44, WHITE)
fill_rect(462, 296, 16, 16, BLACK)
fill_rect(546, 296, 16, 16, BLACK)
# Smile
fill_rect(472, 336, 80, 8, BLACK)
# Body
fill_rect(432, 360, 160, 72, STEEL)
fill_rect(432, 360, 160, 10, DARKGREY)
# Arms
fill_rect(392, 372, 40, 18, STEEL)
fill_rect(592, 372, 40, 18, STEEL)
# Laptop: screen with code lines, then base
fill_rect(352, 392, 320, 84, BLACK)
fill_rect(360, 400, 304, 68, SCREEN)
for i, (lx, lw) in enumerate([(372, 120), (372, 200), (372, 160), (372, 240)]):
    fill_rect(lx, 408 + i * 14, lw, 7, GREEN)
fill_rect(332, 476, 360, 16, DARKGREY)
fill_rect(332, 476, 360, 4, BLACK)

# ---------------------------------------------------------------------------
# Divider + Panel 2: the game (dark "game screen")
# ---------------------------------------------------------------------------
fill_rect(0, 506, W, 12, BLACK)
fill_rect(0, 518, W, H - 518, NAVY)

draw_text("THE GAME:", 512, 542, 4, YELLOW)
draw_text("NO WIN CONDITION", 512, 592, 8, WHITE)
draw_text("47 PLUGINS", 512, 660, 8, WHITE)
draw_text("FINAL BOSS: A DUCK", 512, 728, 8, YELLOW)

# Boss HP bar
fill_rect(312, 800, 400, 26, BLACK)
fill_rect(316, 804, 392, 18, WHITE)
fill_rect(316, 804, 392, 18, RED)
fill_rect(316, 804, 392, 6, (255, 120, 120))
draw_text("BOSS HP", 512, 800, 3, WHITE)  # drawn over bar, white on red

# The duck boss: body, head, beak, eye, wing, crown, feet.
# Feet
fill_rect(452, 992, 44, 12, ORANGE)
fill_rect(528, 992, 44, 12, ORANGE)
# Body
fill_ellipse(512, 956, 96, 52, DUCKY)
# Wing
fill_ellipse(486, 960, 44, 26, DUCKWING)
# Head
fill_circle(596, 904, 46, DUCKY)
# Beak
fill_triangle((634, 892), (682, 904), (634, 918), ORANGE)
fill_triangle((634, 904), (668, 904), (634, 914), (255, 100, 0))
# Eye (angry boss brow)
fill_rect(606, 882, 22, 6, BLACK)
fill_circle(614, 898, 7, BLACK)
# Crown
fill_triangle((566, 870), (578, 838), (590, 870), YELLOW)
fill_triangle((590, 870), (602, 838), (614, 870), YELLOW)
fill_triangle((614, 870), (626, 838), (638, 870), YELLOW)
fill_rect(566, 866, 72, 8, YELLOW)
fill_circle(578, 836, 5, RED)
fill_circle(602, 836, 5, RED)
fill_circle(626, 836, 5, RED)

# Outer border
fill_rect(0, 0, W, 8, BLACK)
fill_rect(0, H - 8, W, 8, BLACK)
fill_rect(0, 0, 8, H, BLACK)
fill_rect(W - 8, 0, 8, H, BLACK)

# ---------------------------------------------------------------------------
# PNG encoder (stdlib only): RGB, no interlace, filter 0
# ---------------------------------------------------------------------------
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += canvas[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


if __name__ == "__main__":
    out = "/output/entry.png"
    n = write_png(out)
    print(f"wrote {out}: {W}x{H}, {n} bytes")
