#!/usr/bin/env python3
"""Draws the trash chute: the linked pipe atlas, the menu icons, and the chute outlet.

The atlas is the part that can be quietly wrong. A linked graphic is sixteen tiles in a 4x4
grid, one per combination of neighbours, and RimWorld picks a tile by bitmask:

    up (north) 1, right (east) 2, down (south) 4, left (west) 8

MaterialAtlasPool takes tile i from column i % 4 and row i // 4 counted from the BOTTOM of
the texture - Unity's UV origin - and samples only the middle three quarters of each tile, the
outer eighth all round being bleed. So tile 0 is bottom-left, tile 15 top-right, and every arm
has to run right out to the tile edge or a seam shows between cells. Get the row order upside
down and every north-south run of chute draws its arms pointing the wrong way; nothing errors.

So after drawing, this samples each tile at the four edge midpoints of its sampled area and
fails unless an arm is present exactly where that tile's bitmask says there is a neighbour.

    python3 Source/Art/riimba_chute.py      # from the repo root
"""

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from riimba_draw import (  # noqa: E402
    BAY_FLOOR, CASE, CASE_DARK, CASE_LIT, CONTACT, OUTLINE, ellipse, finish, new_canvas, rect,
)

OUT_DIR = os.path.join("Mods", "TrashChute", "Textures", "Things", "Building", "Riimba", "Chute")

TILE = 128                      # one atlas tile; the middle 96px is one map cell
PAD = TILE // 8                 # the bleed MaterialAtlasPool never samples
ATLAS = TILE * 4

UP, RIGHT, DOWN, LEFT = 1, 2, 4, 8

HALF_WIDTH = 17                 # half the duct's width, in atlas pixels
ALPHA_THRESHOLD = 40


def tile_origin(index):
    """Top-left of tile `index` in image coordinates (y down)."""
    column = index % 4
    row_from_bottom = index // 4
    return column * TILE, (3 - row_from_bottom) * TILE


def duct(draw, box, horizontal):
    """One straight run: dark casing, a lit top face, and the darker channel down its middle."""
    x0, y0, x1, y1 = box
    rect(draw, box, fill=OUTLINE)
    if horizontal:
        rect(draw, (x0, y0 + 3, x1, y1 - 3), fill=CASE_DARK)
        rect(draw, (x0, y0 + 5, x1, y0 + 5 + (y1 - y0) * 0.35), fill=CASE_LIT)
        rect(draw, (x0, y1 - 13, x1, y1 - 8), fill=BAY_FLOOR)
    else:
        rect(draw, (x0 + 3, y0, x1 - 3, y1), fill=CASE_DARK)
        rect(draw, (x0 + 5, y0, x0 + 5 + (x1 - x0) * 0.35, y1), fill=CASE_LIT)
        rect(draw, (x1 - 13, y0, x1 - 8, y1), fill=BAY_FLOOR)


def hub(draw, cx, cy):
    """The junction box every tile has, so a bend or a tee reads as a fitting, not an overlap."""
    size = HALF_WIDTH + 5
    rect(draw, (cx - size, cy - size, cx + size, cy + size), fill=OUTLINE, radius=5)
    rect(draw, (cx - size + 3, cy - size + 3, cx + size - 3, cy + size - 3), fill=CASE, radius=4)
    rect(draw, (cx - size + 5, cy - size + 5, cx + size - 5, cy - 2), fill=CASE_LIT, radius=3)
    ellipse(draw, (cx - 5, cy - 1, cx + 5, cy + 9), fill=CONTACT)


def draw_tile(draw, index):
    x, y = tile_origin(index)
    cx, cy = x + TILE / 2, y + TILE / 2
    w = HALF_WIDTH

    # Arms run to the very edge of the tile, through the bleed, so neighbouring cells meet.
    if index & UP:
        duct(draw, (cx - w, y, cx + w, cy), horizontal=False)
    if index & DOWN:
        duct(draw, (cx - w, cy, cx + w, y + TILE), horizontal=False)
    if index & LEFT:
        duct(draw, (x, cy - w, cx, cy + w), horizontal=True)
    if index & RIGHT:
        duct(draw, (cx, cy - w, x + TILE, cy + w), horizontal=True)

    hub(draw, cx, cy)


def atlas():
    image, draw = new_canvas(ATLAS, ATLAS)
    for index in range(16):
        draw_tile(draw, index)
    return finish(image, ATLAS, ATLAS)


def menu_icon():
    """A straight east-west run with its fitting, cropped from what the atlas draws."""
    size = TILE
    image, draw = new_canvas(size, size)
    duct(draw, (0, size / 2 - HALF_WIDTH, size, size / 2 + HALF_WIDTH), horizontal=True)
    hub(draw, size / 2, size / 2)
    return finish(image, size, size)


def hidden_menu_icon():
    """The buried chute's menu icon: floor plates, with the duct beneath them shown only as a
    dashed outline - the same run as the ordinary icon, so the two read as a pair, but plainly
    under something rather than on it. It is the only picture the buried chute ever has."""
    size = TILE
    image, draw = new_canvas(size, size)

    # Four floor plates with seams between them.
    gap = 4
    half = size / 2
    for x0, y0 in ((0, 0), (half, 0), (0, half), (half, half)):
        rect(draw, (x0 + gap / 2, y0 + gap / 2, x0 + half - gap / 2, y0 + half - gap / 2),
             fill=CASE_DARK, radius=4)
        rect(draw, (x0 + gap / 2 + 3, y0 + gap / 2 + 3, x0 + half - gap / 2 - 3,
                    y0 + half * 0.45), fill=CASE, radius=3)

    # The duct's edges as dashes, then the fitting as an outline only.
    top, bottom = half - HALF_WIDTH, half + HALF_WIDTH
    dash, space = 12, 8
    x = 4
    while x < size - 4:
        end = min(x + dash, size - 4)
        for y in (top, bottom):
            rect(draw, (x, y - 2, end, y + 2), fill=CASE_LIT)
        x = end + space

    fitting = HALF_WIDTH + 5
    rect(draw, (half - fitting, half - fitting, half + fitting, half + fitting),
         outline=CASE_LIT, width=3, radius=5)
    ellipse(draw, (half - 5, half - 1, half + 5, half + 9), fill=CONTACT)

    return finish(image, size, size)


def outlet():
    size = 192
    m = 16
    image, draw = new_canvas(size, size)
    rect(draw, (m, m, size - m, size - m), fill=OUTLINE, radius=16)
    rect(draw, (m + 3, m + 3, size - m - 3, size - m - 3), fill=CASE_DARK, radius=14)
    rect(draw, (m + 6, m + 6, size - m - 6, size - m - 12), fill=CASE, radius=12)
    rect(draw, (m + 9, m + 9, size - m - 9, m + 9 + (size - 2 * m) * 0.28), fill=CASE_LIT, radius=10)

    # The mouth trash drops out of, and the gold lip around it.
    c = size / 2
    rect(draw, (c - 46, c - 30, c + 46, c + 40), fill=CONTACT, radius=10)
    rect(draw, (c - 40, c - 24, c + 40, c + 34), fill=OUTLINE, radius=8)
    rect(draw, (c - 36, c - 20, c + 36, c + 30), fill=BAY_FLOOR, radius=6)

    return finish(image, size, size)


def verify_atlas(image):
    """Every tile has an arm at exactly the edges its bitmask names, and nowhere else."""
    alpha = image.split()[3]
    failures = []
    inner = TILE - 2 * PAD

    for index in range(16):
        x, y = tile_origin(index)
        x0, y0 = x + PAD, y + PAD           # the sampled area, i.e. one map cell
        mid = inner // 2
        probes = {
            UP: (x0 + mid, y0 + 1),
            DOWN: (x0 + mid, y0 + inner - 2),
            LEFT: (x0 + 1, y0 + mid),
            RIGHT: (x0 + inner - 2, y0 + mid),
        }
        for bit, (px, py) in probes.items():
            present = alpha.getpixel((px, py)) > ALPHA_THRESHOLD
            if present != bool(index & bit):
                name = {UP: "up", DOWN: "down", LEFT: "left", RIGHT: "right"}[bit]
                failures.append(f"tile {index:2d}: {name} arm {'present' if present else 'missing'}"
                                f" but bitmask says {'yes' if index & bit else 'no'}")
    return failures


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    image = atlas()
    failures = verify_atlas(image)
    if failures:
        print("atlas does not match RimWorld's link bitmask layout:")
        for failure in failures:
            print(f"  {failure}")
        return 1

    outputs = {
        "RiimbaTrashChute_Atlas": image,
        "RiimbaTrashChute_MenuIcon": menu_icon(),
        "RiimbaTrashChuteHidden_MenuIcon": hidden_menu_icon(),
        "RiimbaChuteOutlet": outlet(),
    }
    for name, picture in outputs.items():
        path = os.path.join(OUT_DIR, f"{name}.png")
        picture.save(path)
        print(f"wrote {path}")

    print("atlas: all 16 tiles link exactly where their bitmask says")
    return 0


if __name__ == "__main__":
    sys.exit(main())
