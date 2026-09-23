#!/usr/bin/env python3
"""Draws the control station's three linkable facilities.

Each is a single cell, top-down, lit from the top of the screen like the station, and in the
station's own palette so the set reads as one product line: warm-grey casing, dark bay floor,
gold contacts where power goes in, and teal only where something is live.

    fast-charge pad   a low plate with contact rails - the thing a unit would park on
    signal relay      a mast seen from above, with its broadcast rings
    waste hopper      an open-topped bin, the one facility that stores anything

    python3 Source/Art/riimba_facilities.py      # from the repo root
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from riimba_draw import (  # noqa: E402
    BAY_FLOOR, CASE, CASE_DARK, CASE_LIT, CONTACT, OUTLINE, TEAL, TEAL_DARK,
    arc, ellipse, finish, line, new_canvas, polygon, rect,
)

CELL = 192
M = 14          # margin inside the cell, so neighbouring buildings do not visually fuse

OUT_DIR = os.path.join("Textures", "Things", "Building", "Riimba")


def casing(draw, box, radius=16):
    """The station's slab: outline, dark body, lit top band. Same grammar as chassis()."""
    x0, y0, x1, y1 = box
    rect(draw, box, fill=OUTLINE, radius=radius)
    rect(draw, (x0 + 3, y0 + 3, x1 - 3, y1 - 3), fill=CASE_DARK, radius=radius - 2)
    rect(draw, (x0 + 6, y0 + 6, x1 - 6, y1 - 12), fill=CASE, radius=radius - 4)
    rect(draw, (x0 + 9, y0 + 9, x1 - 9, y0 + 9 + (y1 - y0) * 0.30), fill=CASE_LIT,
         radius=radius - 6)


def fast_charge_pad():
    image, draw = new_canvas(CELL, CELL)
    casing(draw, (M, M + 18, CELL - M, CELL - M - 10), radius=18)

    # The plate a unit's contacts meet, with the two gold rails running along it.
    rect(draw, (M + 22, M + 44, CELL - M - 22, CELL - M - 30), fill=BAY_FLOOR, radius=10)
    for x in (CELL * 0.36, CELL * 0.64):
        rect(draw, (x - 7, M + 54, x + 7, CELL - M - 40), fill=CONTACT, radius=3)

    # A bolt in teal between the rails: the one live element, so it reads as "charging".
    cx, cy = CELL / 2, CELL / 2 + 6
    polygon(draw, [(cx + 6, cy - 34), (cx - 16, cy + 4), (cx - 2, cy + 4),
                   (cx - 8, cy + 34), (cx + 16, cy - 6), (cx + 2, cy - 6)], fill=TEAL)

    return finish(image, CELL, CELL)


def signal_relay():
    image, draw = new_canvas(CELL, CELL)
    c = CELL / 2

    # Broadcast rings behind everything, broken like the radius icon so they read as signal.
    for r, width in ((82, 5), (64, 4)):
        for start in (-60, 30, 120, 210):
            arc(draw, (c - r, c - r, c + r, c + r), start, start + 55, fill=TEAL_DARK, width=width)

    # Round base plate and the mast's footing.
    ellipse(draw, (c - 46, c - 46, c + 46, c + 46), fill=OUTLINE)
    ellipse(draw, (c - 43, c - 43, c + 43, c + 43), fill=CASE_DARK)
    ellipse(draw, (c - 39, c - 41, c + 39, c + 33), fill=CASE)
    ellipse(draw, (c - 30, c - 36, c + 30, c - 6), fill=CASE_LIT)

    # The crossbar and the mast head, seen from straight above.
    line(draw, [(c - 34, c), (c + 34, c)], fill=OUTLINE, width=9)
    line(draw, [(c - 32, c - 1), (c + 32, c - 1)], fill=CASE_LIT, width=5)
    ellipse(draw, (c - 15, c - 15, c + 15, c + 15), fill=OUTLINE)
    ellipse(draw, (c - 12, c - 12, c + 12, c + 12), fill=CASE_DARK)
    ellipse(draw, (c - 7, c - 7, c + 7, c + 7), fill=TEAL)

    return finish(image, CELL, CELL)


def waste_hopper():
    image, draw = new_canvas(CELL, CELL)
    casing(draw, (M, M + 10, CELL - M, CELL - M), radius=14)

    # The open mouth, and the funnel walls sloping into it.
    rect(draw, (M + 24, M + 36, CELL - M - 24, CELL - M - 34), fill=OUTLINE, radius=8)
    rect(draw, (M + 28, M + 40, CELL - M - 28, CELL - M - 38), fill=BAY_FLOOR, radius=6)
    for x0, x1 in ((M + 32, CELL / 2 - 10), (CELL - M - 32, CELL / 2 + 10)):
        line(draw, [(x0, M + 46), (x1, CELL / 2 + 10)], fill=CASE_DARK, width=5)

    # A gold lip across the front edge, which is where waste goes in.
    rect(draw, (M + 20, CELL - M - 26, CELL - M - 20, CELL - M - 16), fill=CONTACT, radius=3)

    return finish(image, CELL, CELL)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, make in (("RiimbaFastChargePad", fast_charge_pad),
                       ("RiimbaSignalRelay", signal_relay),
                       ("RiimbaWasteHopper", waste_hopper)):
        path = os.path.join(OUT_DIR, f"{name}.png")
        make().save(path)
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
