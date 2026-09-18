#!/usr/bin/env python3
"""Checks the drone's layers against what the C# will do with them.

The machine is drawn as four layers that turn independently (see Source/Art/README.md):

    shell   the pawn's body graphic, NEVER rotated
    under   drive wheels, rotated to the heading, below the shell
    face    bumper, sensor, lamp, vents, rotated to the heading, above the shell
    brush   hub carried round by the heading, spinning on its own axis, below the shell

Three things can drift apart silently here, and none of them errors at run time:

  1. The brush offset in Defs/ThingDefs_Races/Riimba.xml against what riimba_unit.py's own
     constants imply.
  2. The shell's rotational symmetry. It is the one layer that does not turn, which only
     looks right because a disc looks the same at every angle. Put anything directional on
     it - a vent, an off-centre highlight - and the machine appears to have a fixed front
     that its bumper slides around.
  3. Whether the brush still tucks under the shell at the heading it is authored for.

    python3 Source/Art/verify_brush.py      # from the repo root

Exits non-zero on any mismatch.
"""

import os
import sys
import xml.etree.ElementTree as ET

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import riimba_unit  # noqa: E402

DEF_PATH = os.path.join("Defs", "ThingDefs_Races", "Riimba.xml")
TEXTURE_DIR = os.path.join("Textures", "Things", "Pawn", "Riimba")

BODY_DRAW_SIZE = 1.1
TOLERANCE = 0.0005
ALPHA_THRESHOLD = 40

LAYERS = ("RiimbaShell", "RiimbaUnder", "RiimbaFace", "RiimbaBrush")

# How much of the brush should still show once the shell covers it, at heading 0. The hub sits
# just inside the rim, so roughly a fifth is swallowed. Near 100% means the brush has drifted
# off the machine; far below means it has slid underneath and nothing visibly turns.
MIN_VISIBLE = 0.50
MAX_VISIBLE = 0.95

# The shell never rotates, so it must look the same at every angle. This is the share of pixels
# allowed to disagree between the shell and itself turned 90 degrees - not zero, because
# resampling a rasterised disc never reproduces it exactly.
MAX_ASYMMETRY = 0.03


def comp_props():
    root = ET.parse(DEF_PATH).getroot()

    for comp in root.iter("li"):
        if comp.get("Class") != "RiimbaMod.CompProperties_RiimbaUnit":
            continue
        return {
            "brushAlong": float(comp.findtext("brushAlong")),
            "brushOut": float(comp.findtext("brushOut")),
            "brushDrawSize": float(comp.findtext("brushDrawSize")),
            "brushTexPath": comp.findtext("brushTexPath"),
            "faceTexPath": comp.findtext("faceTexPath"),
            "underTexPath": comp.findtext("underTexPath"),
            "bodyDrawSize": float(comp.findtext("bodyDrawSize")),
        }

    raise SystemExit(f"{DEF_PATH}: no CompProperties_RiimbaUnit found")


def opaque_mask(image):
    return [a > ALPHA_THRESHOLD for a in image.split()[3].tobytes()]


def check_offsets(props, failures):
    side, forward = riimba_unit.brush_offset_in_cells(BODY_DRAW_SIZE)

    expected = {
        "brushAlong": abs(side),
        "brushOut": forward,
        "brushDrawSize": riimba_unit.BRUSH_SIZE / riimba_unit.SIZE * BODY_DRAW_SIZE,
        "bodyDrawSize": BODY_DRAW_SIZE,
    }

    for key, want in expected.items():
        got = props[key]
        if abs(got - want) > TOLERANCE:
            failures.append(f"{key}: def says {got}, art implies {want:.4f}")
        else:
            print(f"{key:>14}: {got}  (art: {want:.4f})")


def check_layers_present(props, failures):
    for name in LAYERS:
        path = os.path.join(TEXTURE_DIR, f"{name}.png")
        if not os.path.exists(path):
            failures.append(f"missing layer texture {path}")

    for key in ("brushTexPath", "faceTexPath", "underTexPath"):
        expected = "Things/Pawn/Riimba/" + {
            "brushTexPath": "RiimbaBrush",
            "faceTexPath": "RiimbaFace",
            "underTexPath": "RiimbaUnder",
        }[key]
        if props[key] != expected:
            failures.append(f"{key}: def says {props[key]}, texture is at {expected}")


def check_shell_symmetry(failures):
    """The shell is the layer that never turns. Prove it can get away with that."""
    path = os.path.join(TEXTURE_DIR, "RiimbaShell.png")
    if not os.path.exists(path):
        return

    shell = Image.open(path).convert("RGBA")
    base = opaque_mask(shell)
    total = sum(base)

    for angle in (90, 180, 270):
        turned = opaque_mask(shell.rotate(angle, resample=Image.BICUBIC))
        differing = sum(1 for a, b in zip(base, turned) if a != b)
        share = differing / total if total else 1.0

        if share > MAX_ASYMMETRY:
            failures.append(
                f"shell differs from itself at {angle} degrees by {share:.1%} "
                f"(limit {MAX_ASYMMETRY:.0%}) - it is not rotationally symmetric, so it will "
                f"read as having a fixed front while the face turns around it")
        else:
            print(f"{'shell at ' + str(angle):>14}: {share:.1%} of pixels differ")


def check_brush_tucks_under(props, failures):
    """At heading 0 the layers stack exactly as authored, so the textures can be composited
    directly to see how much of the brush the shell hides."""
    shell_path = os.path.join(TEXTURE_DIR, "RiimbaShell.png")
    brush_path = os.path.join(TEXTURE_DIR, "RiimbaBrush.png")
    if not (os.path.exists(shell_path) and os.path.exists(brush_path)):
        return

    shell = Image.open(shell_path).convert("RGBA")
    brush = Image.open(brush_path).convert("RGBA")

    # Cells -> body-sprite pixels. Map z runs UP and texture y runs DOWN, hence the negated
    # forward term: the brush is ahead of the machine, which is towards the top of the texture.
    scale = riimba_unit.SIZE / BODY_DRAW_SIZE
    cx = shell.width / 2 + (-props["brushAlong"]) * scale
    cy = shell.height / 2 - props["brushOut"] * scale

    if not (0 <= cx < shell.width and 0 <= cy < shell.height):
        failures.append(f"brush hub at ({cx:.1f},{cy:.1f}) is outside the {shell.width}px sprite")
        return

    layer = Image.new("RGBA", shell.size, (0, 0, 0, 0))
    layer.alpha_composite(brush, (int(round(cx - brush.width / 2)),
                                  int(round(cy - brush.height / 2))))

    brush_mask = opaque_mask(layer)
    shell_mask = opaque_mask(shell)

    total = sum(brush_mask)
    visible = sum(1 for b, o in zip(brush_mask, shell_mask) if b and not o)
    fraction = visible / total if total else 0.0

    if not MIN_VISIBLE <= fraction <= MAX_VISIBLE:
        failures.append(
            f"{fraction:.1%} of the brush shows past the shell, outside the "
            f"{MIN_VISIBLE:.0%}-{MAX_VISIBLE:.0%} band - it is either swallowed by the body "
            f"or floating clear of it")
    else:
        print(f"{'brush':>14}: hub ({cx - shell.width / 2:+.1f},{cy - shell.height / 2:+.1f})px "
              f"from centre, {fraction:.1%} visible past the shell")


def main():
    failures = []
    props = comp_props()

    check_offsets(props, failures)
    check_layers_present(props, failures)
    check_shell_symmetry(failures)
    check_brush_tucks_under(props, failures)

    if failures:
        print("\nFAILED:")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print("\ndrone layers match the def")
    return 0


if __name__ == "__main__":
    sys.exit(main())
