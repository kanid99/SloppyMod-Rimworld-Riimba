#!/usr/bin/env python3
"""Draws the mod's gizmo icons.

Only one so far: the command that sets a station's broadcast radius. It could have
borrowed a vanilla icon - SetTargetFuelLevel is the closest shape of control - but that
one is a fuel drop, and a button whose picture means something else is a button the
player has to learn instead of read.

Command icons are drawn small, on a dark button, and tinted white by default, so this is
line art in near-white with the one teal accent the rest of the mod uses: a ring, the
station inside it, and the sweep marks that say the ring is adjustable.

    python3 Source/Art/riimba_icons.py      # from the repo root
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from riimba_draw import (  # noqa: E402
    TEAL, ellipse, finish, new_canvas, rect,
)

SIZE = 64
INK = (232, 236, 240)

OUT_DIR = os.path.join("Textures", "UI", "Commands")


def stroke_arc(draw, centre, radius, start, sweep, width, fill):
    """An arc stamped from overlapping dots rather than drawn with PIL's arc().

    PIL strokes a wide arc by outlining the band between two radii, which at this size
    comes out visibly beaded. Stamping a disc every half degree costs nothing here and
    gives a clean round stroke with round caps.
    """
    steps = max(2, int(sweep * 2))
    for i in range(steps + 1):
        angle = math.radians(start + sweep * i / steps)
        x = centre + math.cos(angle) * radius
        y = centre + math.sin(angle) * radius
        ellipse(draw, (x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=fill)


def radius_icon():
    image, draw = new_canvas(SIZE, SIZE)
    centre = SIZE / 2

    # The ring, broken at the four diagonals so it reads as a broadcast boundary rather
    # than as a solid rim - a full circle at this size looks like a button, not a range.
    for start in (-80, 10, 100, 190):
        stroke_arc(draw, centre, 25, start, 60, 3.5, INK)

    # Two shorter strokes inside it: the same ring at a smaller setting, which is the
    # whole point of the command.
    for start in (-65, 115):
        stroke_arc(draw, centre, 16, start, 40, 2.5, INK)

    # The station itself, at the centre the radius is measured from. Drawn at the
    # building's own 3:2 proportions so the icon and the thing it configures match.
    rect(draw, (centre - 9, centre - 6, centre + 9, centre + 6), fill=INK, radius=2)
    ellipse(draw, (centre - 3, centre - 3, centre + 3, centre + 3), fill=TEAL)

    return finish(image, SIZE, SIZE)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "RiimbaRadius.png")
    radius_icon().save(path)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
