#!/usr/bin/env python3
"""Checks the brush the C# draws lands where the art says it should.

The side brush used to be painted into the body sprites. It is now its own texture,
positioned and spun at run time from three numbers on CompProperties_RiimbaUnit, which
means the art and the def can now drift apart - and the failure is quiet. Nothing errors;
the brush just hangs off the side of the machine, or sits under it, and the only way to
notice is to look at a drone at the right moment.

So this checks two things mechanically:

  1. The offsets in Defs/ThingDefs_Races/Riimba.xml match what riimba_unit.py computes
     from its own BRUSH_ALONG / BRUSH_OUT constants, and the draw size matches the crop
     the brush texture was cut at.

  2. Placing the brush UNDER each body sprite at those offsets leaves a sensible amount of
     it showing past the shell - not swallowed whole, not floating clear of the machine.

Check 2 is the one that matters, because check 1 only proves two files agree about a
number, not that the number is right.

    python3 Source/Art/verify_brush.py      # from the repo root

Exits non-zero on any mismatch.
"""

import os
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import riimba_unit  # noqa: E402

DEF_PATH = os.path.join("Defs", "ThingDefs_Races", "Riimba.xml")
TEXTURE_DIR = os.path.join("Textures", "Things", "Pawn", "Riimba")

BODY_DRAW_SIZE = 1.1      # PawnKindDef lifeStages bodyGraphicData drawSize
TOLERANCE = 0.0005


def comp_props():
    """The brush fields off CompProperties_RiimbaUnit in the race def."""
    root = ET.parse(DEF_PATH).getroot()

    for comp in root.iter("li"):
        if comp.get("Class") != "RiimbaMod.CompProperties_RiimbaUnit":
            continue
        return {
            "brushAlong": float(comp.findtext("brushAlong")),
            "brushOut": float(comp.findtext("brushOut")),
            "brushDrawSize": float(comp.findtext("brushDrawSize")),
            "brushTexPath": comp.findtext("brushTexPath"),
        }

    raise SystemExit(f"{DEF_PATH}: no CompProperties_RiimbaUnit found")


def expected_from_art():
    """What the art script's own constants imply, in cells."""
    r = riimba_unit.R
    size = riimba_unit.SIZE

    return {
        "brushAlong": r * riimba_unit.BRUSH_ALONG / size * BODY_DRAW_SIZE,
        "brushOut": r * riimba_unit.BRUSH_OUT / size * BODY_DRAW_SIZE,
        "brushDrawSize": riimba_unit.BRUSH_SIZE / size * BODY_DRAW_SIZE,
    }


def hub_pixels(rotation):
    """Where the C# will put the hub, in body-sprite pixels from the sprite centre.

    Reimplements CompRiimbaUnit.BrushOffset and converts back out of cells, so this is
    checking the C#'s construction rather than re-deriving the art's.
    """
    props = comp_props()
    along = props["brushAlong"] / BODY_DRAW_SIZE * riimba_unit.SIZE
    out = props["brushOut"] / BODY_DRAW_SIZE * riimba_unit.SIZE

    # (x, z) in cells -> (x, y) in texture pixels: z is up, texture y is down.
    offsets = {
        "south": (-along, out),
        "north": (along, -out),
        "east": (out, along),
    }
    return offsets[rotation]


# How much of the brush should still be visible once the shell is drawn over it. The hub
# sits just inside the rim, so roughly a fifth is swallowed and the rest reaches past it -
# it measures a shade under 78% for all three rotations.
#
# The band matters in both directions. Near 100% means the brush has drifted off the
# machine and is floating beside it; far below means it has slid under the disc and the
# player sees nothing turning at all. Either way nothing errors at run time, which is the
# whole reason this is checked here.
MIN_VISIBLE = 0.50
MAX_VISIBLE = 0.95

ALPHA_THRESHOLD = 40


def opaque_mask(image):
    return [a > ALPHA_THRESHOLD for a in image.split()[3].tobytes()]


def composite_check(rotation, failures):
    """Place the brush UNDER the body, the way CompRiimbaUnit.PostDraw does, and check
    that a sensible amount of it still reaches past the shell.

    Under, not over: the brush is mounted on the underside of the disc. Drawing it on top
    reads as a spinner sitting on the lid, and an earlier version of this script composited
    it the wrong way round and so agreed with a C# bug that did the same.
    """
    body_path = os.path.join(TEXTURE_DIR, f"Riimba_{rotation}.png")
    brush_path = os.path.join(TEXTURE_DIR, "RiimbaBrush.png")

    if not (os.path.exists(body_path) and os.path.exists(brush_path)):
        failures.append(f"{rotation}: missing texture ({body_path} or {brush_path})")
        return None

    body = Image.open(body_path).convert("RGBA")
    brush = Image.open(brush_path).convert("RGBA")

    dx, dy = hub_pixels(rotation)
    cx = body.width / 2 + dx
    cy = body.height / 2 + dy

    if not (0 <= cx < body.width and 0 <= cy < body.height):
        failures.append(f"{rotation}: hub at ({cx:.1f},{cy:.1f}) is outside the {body.width}px sprite")
        return None

    layer = Image.new("RGBA", body.size, (0, 0, 0, 0))
    layer.alpha_composite(brush, (int(round(cx - brush.width / 2)),
                                  int(round(cy - brush.height / 2))))

    brush_mask = opaque_mask(layer)
    body_mask = opaque_mask(body)

    total = sum(brush_mask)
    visible = sum(1 for b, o in zip(brush_mask, body_mask) if b and not o)
    fraction = visible / total if total else 0.0

    if not MIN_VISIBLE <= fraction <= MAX_VISIBLE:
        failures.append(
            f"{rotation}: {fraction:.1%} of the brush shows past the shell, outside the "
            f"{MIN_VISIBLE:.0%}-{MAX_VISIBLE:.0%} band - it is either swallowed by the body "
            f"or floating clear of it")

    composed = layer.copy()
    composed.alpha_composite(body)
    return fraction


def main():
    failures = []

    actual = comp_props()
    expected = expected_from_art()

    for key, want in expected.items():
        got = actual[key]
        if abs(got - want) > TOLERANCE:
            failures.append(f"{key}: def says {got}, art implies {want:.4f}")
        else:
            print(f"{key:>14}: {got}  (art: {want:.4f})")

    tex = actual["brushTexPath"]
    expected_tex = "Things/Pawn/Riimba/RiimbaBrush"
    if tex != expected_tex:
        failures.append(f"brushTexPath: def says {tex}, textures are at {expected_tex}")

    for rotation in ("south", "north", "east"):
        fraction = composite_check(rotation, failures)
        if fraction is not None:
            dx, dy = hub_pixels(rotation)
            print(f"{rotation:>14}: hub ({dx:+.1f},{dy:+.1f})px from centre, "
                  f"{fraction:.1%} of the brush visible past the shell")

    if failures:
        print("\nFAILED:")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print("\nbrush geometry in the def matches the art")
    return 0


if __name__ == "__main__":
    sys.exit(main())
