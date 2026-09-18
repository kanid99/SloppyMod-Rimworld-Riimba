#!/usr/bin/env python3
"""Draws the Riimba control station's three rotations.

The station is 3x1 and its three docking bays sit one per cell along the edge it
FACES. That is not a decoration: RiimbaSpots.BayCells takes the row of cells outside
rot.FacingCell, and Building_RiimbaStation sends each unit to the bay matching its
roster position. So the art has to put a bay where the C# puts one, for every rotation,
or a unit drives to a blank stretch of casing to charge.

Which means the rotations cannot be made by rotating one image:

    north   the station faces north, so the bays are along the TOP edge
    south   faces south, bays along the BOTTOM edge
    east    faces east, bays along the RIGHT edge, on a 192x576 canvas
    west    not drawn - Graphic_Multi mirrors east, which correctly moves the bays
            to the left edge, and west's FacingCell is (-1, 0, 0)

Light always comes from the top of the screen whatever the rotation, which is why the
south view is drawn rather than flipped: flipping would light the bays from below.

    python3 Source/Art/riimba_station.py      # from the repo root

Run verify_bays.py afterwards - it samples the real textures at the cells the C#
computes and checks a bay is actually there.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from riimba_draw import (  # noqa: E402
    BAY_FLOOR, CASE, CASE_DARK, CASE_LIT, CONTACT, OUTLINE, SHELL_DARK, TEAL,
    TEAL_DARK, ellipse, finish, line, new_canvas, polygon, rect,
)

CELL = 192
CELLS = 3
DEPTH = 2                # cells front-to-back

LONG = CELL * CELLS      # 576
SHORT = CELL * DEPTH     # 384

# How far the machine overhangs its own bays, in cells. This band is drawn a second time as
# a separate texture ABOVE pawn altitude, so a unit reversing in slides under it. Deep enough
# to swallow the back third of a 1.1-cell disc parked on the bay's centre, no deeper - every
# extra pixel is also clipped off any colonist who walks onto the bay.
LIP_DEPTH = 0.35

# How far a bay is cut into the chassis. Kept under a third of the short side: a bay
# deep enough to swallow the casing would leave the station reading as three separate
# docks with a bar behind them rather than as one machine.
BAY_DEPTH = int(CELL * 0.86)
BAY_WIDTH = int(CELL * 0.80)

MARGIN = 6


def chassis(draw, width, height):
    """The case: a rounded slab with a tonal ramp, top lit.

    Flat bands rather than an outline-everything approach - the same grammar the
    vanilla-expanded factory machines use, and what the mending mod's repair centre was
    matched against. Pure black appears only on the silhouette.
    """
    rect(draw, (MARGIN, MARGIN, width - MARGIN, height - MARGIN),
         fill=OUTLINE, radius=14)
    rect(draw, (MARGIN + 3, MARGIN + 3, width - MARGIN - 3, height - MARGIN - 3),
         fill=CASE_DARK, radius=12)

    # The lit face, inset from the top and sides and stopping short of the bottom, so
    # the dark band left underneath is the shadow. One shape, no gradient.
    rect(draw, (MARGIN + 6, MARGIN + 6, width - MARGIN - 6, height - MARGIN - 14),
         fill=CASE, radius=10)
    lit_depth = min(width, height) * 0.42
    rect(draw, (MARGIN + 9, MARGIN + 9, width - MARGIN - 9, MARGIN + 9 + lit_depth),
         fill=CASE_LIT, radius=8)


def bay(draw, cx, cy, horizontal, chevron_towards):
    """One docking bay: a recess, two charging contacts and a chevron.

    The chevron points the way a unit DRIVES IN, which is inwards from the bay towards
    the machine - the opposite of the repair centre's output arrow, and for the same
    reason: an arrow that means something has to follow the thing that moves.
    """
    if horizontal:
        half_w, half_d = BAY_WIDTH / 2, BAY_DEPTH / 2
    else:
        half_w, half_d = BAY_DEPTH / 2, BAY_WIDTH / 2

    rect(draw, (cx - half_w, cy - half_d, cx + half_w, cy + half_d),
         fill=SHELL_DARK, radius=6)
    rect(draw, (cx - half_w + 4, cy - half_d + 4, cx + half_w - 4, cy + half_d - 4),
         fill=BAY_FLOOR, radius=4)

    # Charging contacts, a pair, set across the bay's width.
    spread = (BAY_WIDTH if horizontal else BAY_DEPTH) * 0.22
    for side in (-1, 1):
        if horizontal:
            x, y = cx + side * spread, cy
        else:
            x, y = cx, cy + side * spread
        rect(draw, (x - 7, y - 7, x + 7, y + 7), fill=CONTACT, radius=2)

    # Chevron, pointing chevron_towards: one of "up", "down", "left".
    size = 16
    if chevron_towards == "up":
        pts = [(cx - size, cy + size * 0.7), (cx, cy - size * 0.5), (cx + size, cy + size * 0.7)]
    elif chevron_towards == "down":
        pts = [(cx - size, cy - size * 0.7), (cx, cy + size * 0.5), (cx + size, cy - size * 0.7)]
    else:
        pts = [(cx + size * 0.7, cy - size), (cx - size * 0.5, cy), (cx + size * 0.7, cy + size)]

    polygon(draw, pts, fill=CASE_LIT)


def subcore_window(draw, cx, cy, width, height):
    """The subcore behind armoured glass - the only lit thing on the building, and the
    whole reason the station costs one."""
    rect(draw, (cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2),
         fill=OUTLINE, radius=8)
    rect(draw, (cx - width / 2 + 3, cy - height / 2 + 3, cx + width / 2 - 3, cy + height / 2 - 3),
         fill=TEAL_DARK, radius=6)

    # The core itself: a bright lozenge with a couple of dark seams across it, which is
    # cheaper and reads better than trying to paint a glow.
    inset_w, inset_h = width * 0.33, height * 0.30
    rect(draw, (cx - inset_w, cy - inset_h, cx + inset_w, cy + inset_h),
         fill=TEAL, radius=5)

    # Seams across the short axis of the core, so they read as banding on a solid
    # block rather than as legs coming off a body.
    if width >= height:
        for t in (-0.45, 0.0, 0.45):
            x = cx + inset_w * t * 1.7
            line(draw, [(x, cy - inset_h * 0.8), (x, cy + inset_h * 0.8)],
                 fill=TEAL_DARK, width=3)
    else:
        for t in (-0.45, 0.0, 0.45):
            y = cy + inset_h * t * 1.7
            line(draw, [(cx - inset_w * 0.8, y), (cx + inset_w * 0.8, y)],
                 fill=TEAL_DARK, width=3)


def vent_block(draw, cx, cy, horizontal=True):
    """Cooling slats. Detail as a row of identical marks, which is the only kind of
    fine detail the factory machines carry."""
    span, count = 46, 5
    for i in range(count):
        t = (i - (count - 1) / 2) * (span * 2 / count)
        if horizontal:
            line(draw, [(cx - span, cy + t), (cx + span, cy + t)], fill=CASE_DARK, width=4)
        else:
            line(draw, [(cx + t, cy - span), (cx + t, cy + span)], fill=CASE_DARK, width=4)


def bay_lamp(draw, cx, cy):
    """One lamp per bay, on the casing beside it. Three lamps in a row across the
    building is the casing itself saying how many units it drives - which beats a
    cluster of three lights somewhere else that happens to mean the same thing."""
    ellipse(draw, (cx - 9, cy - 9, cx + 9, cy + 9), fill=CASE_DARK)
    ellipse(draw, (cx - 5, cy - 5, cx + 5, cy + 5), fill=TEAL)


def bay_recess(draw, cx, cy, open_dir):
    """One bay: a recess open on the side the station faces, with charging contacts at its
    closed end and a chevron marking which way the docked unit points.

    The chevron faces OUT, not in. Units reverse into these - they drive up nose-first,
    turn, and back under the overhang - so the nose of a docked unit points out of the bay.
    """
    if open_dir in ("up", "down"):
        half_w, half_d = BAY_WIDTH / 2, BAY_DEPTH / 2
    else:
        half_w, half_d = BAY_DEPTH / 2, BAY_WIDTH / 2

    rect(draw, (cx - half_w, cy - half_d, cx + half_w, cy + half_d),
         fill=SHELL_DARK, radius=8)
    rect(draw, (cx - half_w + 5, cy - half_d + 5, cx + half_w - 5, cy + half_d - 5),
         fill=BAY_FLOOR, radius=6)

    # Contacts sit slightly OUTBOARD of the bay's centre, not against its closed end.
    # Against the closed end they landed under the overhang and were invisible - and
    # verify_bays.py keys off this gold as its "a bay is here" marker, so a hidden contact
    # is a broken check as well as wasted pixels.
    out = {"down": (0, 1), "up": (0, -1), "right": (1, 0)}[open_dir]
    spread = 28
    for side in (-1, 1):
        if out[0]:
            x = cx + out[0] * (half_w * 0.34)
            y = cy + side * spread
        else:
            x = cx + side * spread
            y = cy + out[1] * (half_d * 0.34)
        rect(draw, (x - 8, y - 8, x + 8, y + 8), fill=CONTACT, radius=2)

    size = 18
    if open_dir == "down":
        pts = [(cx - size, cy + size * 0.2), (cx, cy + size * 1.1), (cx + size, cy + size * 0.2)]
    elif open_dir == "up":
        pts = [(cx - size, cy - size * 0.2), (cx, cy - size * 1.1), (cx + size, cy - size * 0.2)]
    else:
        pts = [(cx - size * 0.2, cy - size), (cx + size * 1.1, cy), (cx - size * 0.2, cy + size)]
    polygon(draw, pts, fill=CASE_LIT)


def lip_band(draw, box, shadow_edge):
    """The overhang: the machine protruding over the closed end of its bays.

    Drawn into the base sprite so the station looks solid, and again into a separate
    texture that Building_RiimbaStation draws above pawn altitude. A unit reversing in
    passes under that second copy.

    The dark line along its open edge is what sells it as an overhang rather than a
    painted stripe - it is the underside catching no light.
    """
    x0, y0, x1, y1 = box
    rect(draw, (x0, y0, x1, y1), fill=CASE)
    rect(draw, (x0, y0, x1, y1 - (y1 - y0) * 0.55) if shadow_edge == "down"
         else (x0, y0 + (y1 - y0) * 0.55, x1, y1) if shadow_edge == "up"
         else (x0, y0, x1 - (x1 - x0) * 0.55, y1), fill=CASE_LIT)

    if shadow_edge == "down":
        rect(draw, (x0, y1 - 7, x1, y1), fill=OUTLINE)
    elif shadow_edge == "up":
        rect(draw, (x0, y0, x1, y0 + 7), fill=OUTLINE)
    else:
        rect(draw, (x1 - 7, y0, x1, y1), fill=OUTLINE)


def horizontal_geometry(bays_at_top):
    """Where the rows and the lip sit, for a station facing north or south."""
    lip_px = CELL * LIP_DEPTH

    if bays_at_top:
        front_y0, front_y1 = 0, CELL              # bays occupy the top row
        lip_box = (MARGIN, CELL - lip_px, LONG - MARGIN, CELL)
        open_dir, shadow = "up", "up"
        body_y = CELL * 1.5
    else:
        front_y0, front_y1 = CELL, SHORT          # bays occupy the bottom row
        lip_box = (MARGIN, CELL, LONG - MARGIN, CELL + lip_px)
        open_dir, shadow = "down", "down"
        body_y = CELL * 0.5

    return front_y0, front_y1, lip_box, open_dir, shadow, body_y


def draw_horizontal(bays_at_top):
    image, draw = new_canvas(LONG, SHORT)
    chassis(draw, LONG, SHORT)

    front_y0, front_y1, lip_box, open_dir, shadow, body_y = horizontal_geometry(bays_at_top)

    subcore_window(draw, LONG / 2, body_y, 150, 62)
    vent_block(draw, CELL * 0.5, body_y, horizontal=True)
    vent_block(draw, CELL * 2.5, body_y, horizontal=True)

    bay_cy = (front_y0 + front_y1) / 2
    for i in range(CELLS):
        bay_recess(draw, CELL * (i + 0.5), bay_cy, open_dir)

    lip_band(draw, lip_box, shadow)
    for i in range(CELLS):
        bay_lamp(draw, CELL * (i + 0.5), (lip_box[1] + lip_box[3]) / 2)

    return finish(image, LONG, SHORT)


def draw_horizontal_lip(bays_at_top):
    """The overhang alone, on a transparent canvas the same size as the station."""
    image, draw = new_canvas(LONG, SHORT)
    _, _, lip_box, _, shadow, _ = horizontal_geometry(bays_at_top)

    lip_band(draw, lip_box, shadow)
    for i in range(CELLS):
        bay_lamp(draw, CELL * (i + 0.5), (lip_box[1] + lip_box[3]) / 2)

    return finish(image, LONG, SHORT)


def east_geometry():
    lip_px = CELL * LIP_DEPTH
    return (CELL, SHORT), (CELL, MARGIN, CELL + lip_px, LONG - MARGIN), "right", "right", CELL * 0.5


def draw_east():
    image, draw = new_canvas(SHORT, LONG)
    chassis(draw, SHORT, LONG)

    lip_box, open_dir, shadow, body_x = east_geometry()[1:]

    subcore_window(draw, body_x, LONG / 2, 62, 150)
    vent_block(draw, body_x, CELL * 0.5, horizontal=False)
    vent_block(draw, body_x, CELL * 2.5, horizontal=False)

    for i in range(CELLS):
        bay_recess(draw, CELL * 1.5, CELL * (i + 0.5), open_dir)

    lip_band(draw, lip_box, shadow)
    for i in range(CELLS):
        bay_lamp(draw, (lip_box[0] + lip_box[2]) / 2, CELL * (i + 0.5))

    return finish(image, SHORT, LONG)


def draw_east_lip():
    image, draw = new_canvas(SHORT, LONG)
    lip_box, _, shadow, _ = east_geometry()[1:]

    lip_band(draw, lip_box, shadow)
    for i in range(CELLS):
        bay_lamp(draw, (lip_box[0] + lip_box[2]) / 2, CELL * (i + 0.5))

    return finish(image, SHORT, LONG)


def main():
    out_dir = os.path.join("Textures", "Things", "Building", "Riimba")
    os.makedirs(out_dir, exist_ok=True)

    views = {
        "north": (lambda: draw_horizontal(bays_at_top=True), lambda: draw_horizontal_lip(True)),
        "south": (lambda: draw_horizontal(bays_at_top=False), lambda: draw_horizontal_lip(False)),
        "east": (draw_east, draw_east_lip),
    }

    for name, (body, lip) in views.items():
        path = os.path.join(out_dir, f"RiimbaStation_{name}.png")
        body().save(path)
        print(f"wrote {path}")

        lip_path = os.path.join(out_dir, f"RiimbaStationLip_{name}.png")
        lip().save(lip_path)
        print(f"wrote {lip_path}")


if __name__ == "__main__":
    main()
