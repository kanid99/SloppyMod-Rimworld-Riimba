#!/usr/bin/env python3
"""Draws the Riimba drone's three rotations.

RimWorld's camera never rotates, so the three sprites are three VIEWS of the same
object, not three rotations of one image. Turning the south sprite 180 degrees would
put the sensor on the far side of the disc but also put its highlight on the bottom,
lit from below, which reads as a hole rather than a bump.

So each view is drawn: south shows the face (sensor and bumper towards the camera),
north shows the back (vent grille and lifting handle), east shows the profile with the
face to the right. West is not drawn at all - Graphic_Multi mirrors east for west, and
a disc is symmetric about that axis.

    python3 Source/Art/riimba_unit.py      # from the repo root
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from riimba_draw import (  # noqa: E402
    BRUSH, BRUSH_DARK, BUMPER, BUMPER_DARK, OUTLINE, PANEL, SHELL, SHELL_DARK,
    SHELL_LIT, TEAL, TEAL_DARK, arc, ellipse, finish, line, new_canvas, pieslice,
    polygon, rect,
)

SIZE = 256

# The disc, inset from the canvas edge so the brush and bumper have somewhere to sit
# without touching the texture border - a sprite that runs to its own edge gets clipped
# by the mesh at some zoom levels.
CX = CY = SIZE / 2
R = SIZE * 0.36


def disc_box(radius):
    return (CX - radius, CY - radius, CX + radius, CY + radius)


def draw_body(draw):
    """The shell: a dark rim, a lit upper face, and a recessed top panel.

    Depth is tone, not outline. The rim is a full disc in the dark tone and the lit
    face is a slightly smaller disc offset UP by a few pixels, which leaves a thicker
    dark crescent along the bottom - the whole of the shading, done with two ellipses.
    """
    ellipse(draw, disc_box(R), fill=OUTLINE)
    ellipse(draw, disc_box(R - 2), fill=SHELL_DARK)

    lit = R - 5
    ellipse(draw, (CX - lit, CY - lit - 3, CX + lit, CY + lit - 3), fill=SHELL)

    # Top face, brighter still, offset further up. Three discs is enough: any more and
    # it starts to look like a rendered sphere, which is not the register the rest of
    # the game's top-down art is in.
    face = R - 13
    ellipse(draw, (CX - face, CY - face - 5, CX + face, CY + face - 5), fill=SHELL_LIT)

    # Recessed centre panel - the lid over the bin.
    panel = R * 0.48
    ellipse(draw, (CX - panel, CY - panel - 4, CX + panel, CY + panel - 4),
            fill=SHELL_DARK)
    ellipse(draw, (CX - panel + 2, CY - panel - 2, CX + panel - 2, CY + panel - 6),
            fill=PANEL)

    # A highlight along the lid's upper rim only. One arc, the same trick as the shell:
    # light from above, so the top edge catches and the bottom edge does not.
    arc(draw, (CX - panel, CY - panel - 4, CX + panel, CY + panel - 4),
        200, 340, fill=SHELL_LIT, width=2)


def draw_wheels(draw, horizontal=True):
    """Drive wheels, peeking out either side of the shell.

    Only ever a sliver: they are underneath a disc that sits on the floor, so almost
    all of each wheel is hidden. Drawing them proud of the shell is what stops the unit
    reading as a floating puck.
    """
    # Centred just OUTSIDE the rim, not under it. An earlier version had these at 0.80R
    # with the shell drawn over the top, which hid them completely and left the unit
    # reading as a floating puck.
    inset = R * 0.97
    length = R * 0.42
    thickness = R * 0.20

    if horizontal:
        for side in (-1, 1):
            x = CX + side * inset
            rect(draw, (x - thickness / 2, CY - length / 2, x + thickness / 2, CY + length / 2),
                 fill=SHELL_DARK, radius=thickness * 0.4)
    else:
        for side in (-1, 1):
            y = CY + side * inset
            rect(draw, (CX - length / 2, y - thickness / 2, CX + length / 2, y + thickness / 2),
                 fill=SHELL_DARK, radius=thickness * 0.4)


def draw_bumper(draw, facing):
    """The sprung bumper arc across the leading edge.

    `facing` is the compass direction the FRONT of the unit points on screen: "down"
    for the south view, "up" for north, "right" for east.
    """
    span = {"down": (20, 160), "up": (200, 340), "right": (290, 70)}[facing]
    box = disc_box(R - 1)

    arc(draw, box, span[0], span[1], fill=BUMPER_DARK, width=6)
    arc(draw, disc_box(R - 3), span[0], span[1], fill=BUMPER, width=3.5)


def draw_sensor(draw, facing):
    """The sensor ring: the one saturated thing on the model, and the unit's 'front'.

    A raised turret rather than a flat decal - the dark collar under the teal is what
    gives it height, and it is the only part of the sprite with a hard outline.
    """
    offset = R * 0.52
    dx, dy = {"down": (0, 1), "up": (0, -1), "right": (1, 0)}[facing]
    x = CX + dx * offset
    y = CY + dy * offset - 4

    collar = R * 0.22
    ellipse(draw, (x - collar, y - collar, x + collar, y + collar),
            fill=SHELL_DARK, outline=OUTLINE, width=1.5)

    lens = collar * 0.62
    ellipse(draw, (x - lens, y - lens, x + lens, y + lens), fill=TEAL_DARK)

    inner = lens * 0.62
    ellipse(draw, (x - inner, y - inner, x + inner, y + inner), fill=TEAL)


def draw_vents(draw, facing):
    """Exhaust slats on the back, so the north view is not just the south view
    with the eye rubbed out."""
    offset = R * 0.52
    dx, dy = {"up": (0, 1), "down": (0, -1), "right": (-1, 0)}[facing]

    for i in (-1, 0, 1):
        if dx:
            x = CX + dx * offset
            y = CY - 4 + i * (R * 0.18)
            line(draw, [(x - R * 0.16, y), (x + R * 0.16, y)], fill=SHELL_DARK, width=2.5)
        else:
            x = CX + i * (R * 0.18)
            y = CY + dy * offset - 4
            line(draw, [(x, y - R * 0.16), (x, y + R * 0.16)], fill=SHELL_DARK, width=2.5)


def draw_handle(draw):
    """A lifting handle across the lid, visible from behind. Purely so the north view
    has something of its own to say."""
    width = R * 0.46
    rect(draw, (CX - width, CY - 11, CX + width, CY - 3),
         fill=SHELL, outline=OUTLINE, width=1.5, radius=4)
    line(draw, [(CX - width + 3, CY - 8.5), (CX + width - 3, CY - 8.5)],
         fill=SHELL_LIT, width=1.5)


# Where the brush hub sits relative to the disc's centre, as multiples of R. The body
# sprites no longer draw the brush at all - it is its own texture now, positioned and
# spun at run time - but these still define where it goes, and the C# has to agree with
# them or the brush floats off the machine. verify_brush.py checks that it does.
BRUSH_ALONG = 0.50
BRUSH_OUT = 0.97

# Canvas for the standalone brush. Deliberately a crop of the SAME 256px sprite scale,
# so the brush keeps its original size in game: 64/256 of the body's drawSize.
BRUSH_SIZE = 64


def brush_hub(facing):
    """Hub position in body-sprite pixels, measured from the sprite's centre."""
    along = R * BRUSH_ALONG
    out = R * BRUSH_OUT

    if facing == "down":
        return -along, out
    if facing == "up":
        return along, -out
    return out, along


def view_brush():
    """The spinner alone, hub dead centre.

    Centred is the whole point: the C# rotates this quad about its own middle, so an
    off-centre hub would make the brush orbit a point beside itself instead of turning
    on the spot.

    Drawn at the body's scale rather than blown up to fill the canvas, so it stays the
    size it always was once the two are composited back together in game.
    """
    image, draw = new_canvas(BRUSH_SIZE, BRUSH_SIZE)
    cx = cy = BRUSH_SIZE / 2
    spin = R * 0.26

    import math

    for i in range(6):
        angle = i * 60 + 15
        ax = cx + spin * math.cos(math.radians(angle))
        ay = cy + spin * math.sin(math.radians(angle))
        line(draw, [(cx, cy), (ax, ay)], fill=BRUSH_DARK, width=5)
        line(draw, [(cx, cy), (ax, ay)], fill=BRUSH, width=2.5)

    hub = R * 0.12
    ellipse(draw, (cx - hub, cy - hub, cx + hub, cy + hub),
            fill=SHELL_DARK, outline=OUTLINE, width=1)
    ellipse(draw, (cx - hub * 0.45, cy - hub * 0.45, cx + hub * 0.45, cy + hub * 0.45),
            fill=SHELL_LIT)

    return finish(image, BRUSH_SIZE, BRUSH_SIZE)


def draw_status_led(draw):
    """The charge light on the lid, set BEHIND the sensor rather than at a fixed point.

    Fixed at top centre it drifted off the lid on the east view and looked like a
    sticker someone had put on at random."""
    dx, dy = {"down": (0, -1), "up": (0, 1), "right": (-1, 0)}["down"]
    _place_led(draw, dx, dy)


def _place_led(draw, dx, dy):
    # Half the sensor's size, and no dark collar. At parity with the sensor the two
    # teal dots read as a pair of eyes; the point of this one is that it is a pilot
    # lamp, subordinate to the thing that actually looks where the unit is going.
    offset = R * 0.30
    led = R * 0.055
    x = CX + dx * offset
    y = CY + dy * offset - 4

    ellipse(draw, (x - led, y - led, x + led, y + led), fill=TEAL)


# ---------------------------------------------------------------------------------
# Four layers, not three views.
#
# The unit turns to any heading now, so it cannot be three fixed sprites. It is split by
# what each part does when the machine turns:
#
#   shell   the disc and its lid. Rotationally symmetric, so it NEVER rotates - which is
#           what keeps its highlight lit from the top of the screen at every heading.
#           Drawn by the pawn renderer as the body graphic.
#   under   the drive wheels. They turn with the machine, and they live beneath the shell.
#   face    bumper, sensor, pilot lamp, vents, handle. Everything that says which way the
#           machine is pointing. Turns with the heading, drawn above the shell.
#   brush   the spinner. Its hub is carried round by the heading AND it turns on its own
#           axis while cleaning.
#
# The three rotating layers are authored pointing NORTH - front at the TOP of the texture -
# because that is the convention Graphic.Draw's extraRotation expects, the same one vanilla
# projectiles use. IntVec3.AngleFlat gives 0 for north, so heading feeds straight in.
# ---------------------------------------------------------------------------------


def view_shell():
    """The disc alone. Nothing here may hint at a direction."""
    image, draw = new_canvas(SIZE, SIZE)
    draw_body(draw)
    return finish(image, SIZE, SIZE)


def view_under():
    """Drive wheels, which turn with the machine and sit beneath the shell."""
    image, draw = new_canvas(SIZE, SIZE)
    draw_wheels(draw, horizontal=True)
    return finish(image, SIZE, SIZE)


def view_face():
    """Everything that shows which way the machine points, front at the top."""
    image, draw = new_canvas(SIZE, SIZE)
    draw_bumper(draw, "up")
    draw_vents(draw, "up")
    draw_handle(draw)
    draw_sensor(draw, "up")
    _place_led(draw, 0, -1)
    return finish(image, SIZE, SIZE)


def brush_offset_in_cells(body_draw_size=1.1):
    """The hub's offset from the centre as (side, forward) in cells.

    Not per-rotation any more: the C# rotates this pair by the unit's heading, so one pair
    covers every angle. Forward is towards the bumper, side is to the machine's right.
    """
    side = -R * BRUSH_ALONG / SIZE * body_draw_size
    forward = R * BRUSH_OUT / SIZE * body_draw_size
    return side, forward


def main():
    out_dir = os.path.join("Textures", "Things", "Pawn", "Riimba")
    os.makedirs(out_dir, exist_ok=True)

    for name, view in (("RiimbaShell", view_shell), ("RiimbaUnder", view_under),
                       ("RiimbaFace", view_face), ("RiimbaBrush", view_brush)):
        path = os.path.join(out_dir, f"{name}.png")
        view().save(path)
        print(f"wrote {path}")

    side, forward = brush_offset_in_cells()
    print()
    print("These must match CompProperties_RiimbaUnit in Defs/ThingDefs_Races/Riimba.xml:")
    print(f"  brushDrawSize {BRUSH_SIZE / SIZE * 1.1:.4f}")
    print(f"  brushAlong    {abs(side):.4f}   (hub offset to the side)")
    print(f"  brushOut      {forward:.4f}   (hub offset forward)")


if __name__ == "__main__":
    main()
