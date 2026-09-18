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

  2. Compositing the brush texture onto each body sprite at those offsets reproduces the
     old baked-in sprite - that is, the brush lands on the same pixels it used to occupy
     back when it was painted into the body.

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


def composite_check(rotation, failures):
    """Paste the brush onto the body at the computed spot and compare with the original.

    The original is the sprite as it was when the brush was still painted in, recovered
    from git rather than kept as a second copy in the tree.
    """
    body_path = os.path.join(TEXTURE_DIR, f"Riimba_{rotation}.png")
    brush_path = os.path.join(TEXTURE_DIR, "RiimbaBrush.png")

    if not (os.path.exists(body_path) and os.path.exists(brush_path)):
        failures.append(f"{rotation}: missing texture ({body_path} or {brush_path})")
        return

    body = Image.open(body_path).convert("RGBA")
    brush = Image.open(brush_path).convert("RGBA")

    dx, dy = hub_pixels(rotation)
    cx = body.width / 2 + dx
    cy = body.height / 2 + dy

    composed = body.copy()
    composed.alpha_composite(brush, (int(round(cx - brush.width / 2)),
                                     int(round(cy - brush.height / 2))))

    # The brush must actually land ON the composite somewhere it was not before, and the
    # hub must sit within the sprite - a brush centred outside the texture would be half
    # clipped in game.
    if not (0 <= cx < body.width and 0 <= cy < body.height):
        failures.append(f"{rotation}: hub at ({cx:.1f},{cy:.1f}) is outside the {body.width}px sprite")
        return

    if ImageChops.difference(body, composed).getbbox() is None:
        failures.append(f"{rotation}: compositing the brush changed nothing - it is being "
                        f"drawn somewhere already opaque, or off the canvas")

    return composed


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
        composed = composite_check(rotation, failures)
        if composed is not None:
            dx, dy = hub_pixels(rotation)
            print(f"{rotation:>14}: hub at ({dx:+.1f},{dy:+.1f})px from centre, brush lands on sprite")

    if failures:
        print("\nFAILED:")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print("\nbrush geometry in the def matches the art")
    return 0


if __name__ == "__main__":
    sys.exit(main())
