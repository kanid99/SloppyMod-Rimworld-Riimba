#!/usr/bin/env python3
"""Checks the station art agrees with RiimbaSpots about where the bays are.

This exists because the mending mod shipped an east texture with its ports on the wrong
cells and nobody caught it by looking. The failure is quiet in exactly the same way
here: a station rotated east would still work, units would still charge, and the only
symptom would be a drone parked on a blank stretch of casing.

So the check is mechanical. RiimbaSpots.BayCells is reimplemented below from the C#,
run for all four rotations against the 3x2 footprint, and the resulting cells are
translated into pixel positions in whichever texture that rotation draws. A bay must be
found at each of them, and the opposite edge must be clear.

The overhang gets the same treatment, for the same reason. It is a mask, and a mask that masks
too little is indistinguishable from one that is not drawn at all - which is how it shipped
once: the overhang was drawn from a DrawAt the engine never called, because BuildingBase is
MapMeshOnly. So the real drone sprite is composited onto each bay at the size the def gives it,
and the overhang must swallow a healthy share of it and leave none of it showing on the far
side of the band. That second test has slack in it today, because the shell's disc is narrower
than its sprite and stops short of the seam; it is there for the day bodyDrawSize grows and a
crescent of drone starts appearing on top of the machine.

    python3 Source/Art/verify_bays.py      # from the repo root

Exits non-zero on any mismatch, so it can be wired into a build.
"""

import os
import sys
import xml.etree.ElementTree as ET

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from riimba_draw import CONTACT  # noqa: E402

TEXTURE_DIR = os.path.join("Textures", "Things", "Building", "Riimba")
UNIT_TEXTURE_DIR = os.path.join("Textures", "Things", "Pawn", "Riimba")
UNIT_DEF_PATH = os.path.join("Defs", "ThingDefs_Races", "Riimba.xml")

CELL_PX = 192
SIZE = (3, 2)          # the def's <size>: three wide, two deep

ALPHA_THRESHOLD = 40

# How much of a docked unit the overhang should hide. Too little and it reads as parked
# against the machine rather than driven into it; too much and the unit disappears, which
# loses the animation the masking exists to sell in the first place.
MIN_MASKED = 0.30
MAX_MASKED = 0.70

# Rot4: 0 north, 1 east, 2 south, 3 west. FacingCell as the game defines it.
FACING = {
    "north": (0, 1),
    "east": (1, 0),
    "south": (0, -1),
    "west": (-1, 0),
}

# Which texture each rotation draws, and whether Graphic_Multi mirrors it. West has no
# texture of its own - it reuses east, flipped horizontally.
TEXTURE_FOR = {
    "north": ("north", False),
    "east": ("east", False),
    "south": ("south", False),
    "west": ("east", True),
}


def footprint(rot):
    """The occupied rect, with the size's axes swapped for the vertical rotations - which
    is what GenAdj.OccupiedRect does."""
    if rot in ("north", "south"):
        return 0, SIZE[0] - 1, 0, SIZE[1] - 1
    return 0, SIZE[1] - 1, 0, SIZE[0] - 1


def bay_cells(rot):
    """RiimbaSpots.BayCells, reimplemented.

    The bays are the front row INSIDE the footprint, not the row outside it. That is what
    lets a docking unit drive onto the building's own cells and slide under its overhang.
    """
    min_x, max_x, min_z, max_z = footprint(rot)
    dx, dz = FACING[rot]

    if dx != 0:
        x = max_x if dx > 0 else min_x
        return [(x, z) for z in range(min_z, max_z + 1)]

    z = max_z if dz > 0 else min_z
    return [(x, z) for x in range(min_x, max_x + 1)]


def looks_like_bay(image, px, py, radius=26):
    """True if the gold charging-contact colour appears near this point.

    The contacts are the one colour that appears nowhere else on the building, which
    makes them a cleaner marker than the bay recess - the recess tone is close to the
    chassis shadow.
    """
    width, height = image.size

    for x in range(max(0, px - radius), min(width, px + radius)):
        for y in range(max(0, py - radius), min(height, py + radius)):
            r, g, b, a = image.getpixel((x, y))
            if a < 128:
                continue
            if abs(r - CONTACT[0]) < 34 and abs(g - CONTACT[1]) < 34 and abs(b - CONTACT[2]) < 34:
                return True

    return False


def row_centres(image, rot, front):
    """Texture-space centres of the three cells in the front or back row.

    Screen y runs DOWN and map z runs UP, so a north-facing station's front row is the TOP
    of its texture. Getting that inversion wrong is precisely the bug this script exists to
    catch - the mending mod shipped it once.
    """
    width, height = image.size
    dx, dz = FACING[rot]

    if dx != 0:
        # East or west facing: two columns, three rows of bays.
        near = dx > 0
        x = width * 0.75 if (near if front else not near) else width * 0.25
        return [(int(x), int(height * (i + 0.5) / 3)) for i in range(3)]

    near = dz > 0
    y = height * 0.25 if (near if front else not near) else height * 0.75
    return [(int(width * (i + 0.5) / 3), int(y)) for i in range(3)]


def bay_sample_points(image, rot):
    return row_centres(image, rot, front=True)


def opposite_points(image, rot):
    return row_centres(image, rot, front=False)


def body_draw_size():
    """The unit's bodyDrawSize, read off the def rather than hardcoded - the whole point is
    to check the art against what the game will actually do."""
    root = ET.parse(UNIT_DEF_PATH).getroot()

    for comp in root.iter("li"):
        if comp.get("Class") == "RiimbaMod.CompProperties_RiimbaUnit":
            return float(comp.findtext("bodyDrawSize"))

    raise SystemExit(f"{UNIT_DEF_PATH}: no CompProperties_RiimbaUnit found")


def opaque_mask(image):
    alpha = image.split()[3].tobytes()
    width = image.width
    return {(i % width, i // width) for i, a in enumerate(alpha) if a > ALPHA_THRESHOLD}


def frontness(rot):
    """A function giving how far towards the station's open edge a texture pixel is.

    Map z runs UP and texture y runs DOWN, so a north-facing station - dz +1 - has its open
    edge at the TOP of its texture, where y is smallest. Hence the negations.
    """
    dx, dz = FACING[rot]

    if dx > 0:
        return lambda x, y: x
    if dx < 0:
        return lambda x, y: -x
    if dz > 0:
        return lambda x, y: -y
    return lambda x, y: y


def docked_unit_mask(station_size, centre, draw_size):
    """The real drone sprite, at the size the def draws it, parked on a bay centre."""
    shell = Image.open(os.path.join(UNIT_TEXTURE_DIR, "RiimbaShell.png")).convert("RGBA")
    side = int(round(draw_size * CELL_PX))
    shell = shell.resize((side, side), resample=Image.BICUBIC)

    layer = Image.new("RGBA", station_size, (0, 0, 0, 0))
    layer.alpha_composite(shell, (int(round(centre[0] - side / 2)),
                                  int(round(centre[1] - side / 2))))
    return opaque_mask(layer)


def check_overhang_masks_unit(rot, station, lip, draw_size, failures):
    """The overhang has to hide the back of a docked unit, and hide ALL of the part that is
    further in than the band's open edge."""
    lip_mask = opaque_mask(lip)
    if not lip_mask:
        return

    toward_front = frontness(rot)
    # The open edge of the band: the frontmost overhang pixel. Everything from here inwards
    # is behind the overhang as far as the player's eye is concerned.
    open_edge = max(toward_front(x, y) for x, y in lip_mask)

    for i, centre in enumerate(bay_sample_points(station, rot)):
        unit = docked_unit_mask(station.size, centre, draw_size)
        if not unit:
            continue

        masked = len(unit & lip_mask)
        fraction = masked / len(unit)

        # Pixels of the unit that lie inwards of the band's open edge but are not covered:
        # the crescent that gives the effect away.
        leaked = sum(1 for x, y in unit
                     if toward_front(x, y) <= open_edge and (x, y) not in lip_mask)

        if leaked > 0:
            failures.append(
                f"{rot}: {leaked} px of a unit docked at bay {i} show past the inner edge of "
                f"the overhang - it would appear to sit on top of the station. Raise LIP_INSET "
                f"in riimba_station.py.")
        elif not MIN_MASKED <= fraction <= MAX_MASKED:
            failures.append(
                f"{rot}: the overhang hides {fraction:.1%} of a unit docked at bay {i}, outside "
                f"the {MIN_MASKED:.0%}-{MAX_MASKED:.0%} band - adjust LIP_DEPTH in "
                f"riimba_station.py.")
        elif i == 1:
            print(f"{'':>6}  overhang hides {fraction:.1%} of a unit on the centre bay, "
                  f"nothing showing past it")


def main():
    failures = []
    draw_size = body_draw_size()

    for rot in ("north", "east", "south", "west"):
        texture_name, mirrored = TEXTURE_FOR[rot]
        path = os.path.join(TEXTURE_DIR, f"RiimbaStation_{texture_name}.png")

        if not os.path.exists(path):
            failures.append(f"{rot}: missing texture {path}")
            continue

        image = Image.open(path).convert("RGBA")
        if mirrored:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)

        cells = bay_cells(rot)
        if len(cells) != 3:
            failures.append(f"{rot}: BayCells returned {len(cells)} cells, expected 3")

        for i, (px, py) in enumerate(bay_sample_points(image, rot)):
            if not looks_like_bay(image, px, py):
                failures.append(
                    f"{rot}: no bay in the texture at bay {i} ({px},{py}) - "
                    f"the C# puts that bay at map cell {cells[i]}")

        for i, (px, py) in enumerate(opposite_points(image, rot)):
            if looks_like_bay(image, px, py):
                failures.append(
                    f"{rot}: found a bay in the BACK row at ({px},{py}) - "
                    f"the facing side is {FACING[rot]}, so this rotation is reversed")

        # The overhang is a separate texture the building draws above pawn altitude. It has
        # to exist for every rotation, or a unit reverses in and simply sits on top of the
        # machine with nothing masking it.
        lip_path = os.path.join(TEXTURE_DIR, f"RiimbaStationLip_{texture_name}.png")
        if not os.path.exists(lip_path):
            failures.append(f"{rot}: missing overhang texture {lip_path}")
        else:
            lip = Image.open(lip_path).convert("RGBA")
            if mirrored:
                lip = lip.transpose(Image.FLIP_LEFT_RIGHT)
            if lip.size != image.size:
                failures.append(f"{rot}: overhang is {lip.size}, station is {image.size} - "
                                f"they are drawn at the same rect, so they must match")
            elif lip.getbbox() is None:
                failures.append(f"{rot}: overhang texture is entirely transparent")
            else:
                check_overhang_masks_unit(rot, image, lip, draw_size, failures)

        print(f"{rot:>6}: texture {texture_name}"
              f"{' (mirrored)' if mirrored else ''}, bay cells {cells}")

    if failures:
        print("\nFAILED:")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print("\nall rotations agree with RiimbaSpots.BayCells")
    return 0


if __name__ == "__main__":
    sys.exit(main())
