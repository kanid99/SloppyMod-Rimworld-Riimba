# Riimba artwork

Every sprite in this mod is drawn from primitives by the scripts in this folder. No
image generator is involved and there are no source PSDs, so the art rebuilds from a
clean checkout with nothing installed but Pillow.

```sh
pip install pillow
python3 Source/Art/riimba_unit.py       # the drone, three views
python3 Source/Art/riimba_station.py    # the station, three rotations
python3 Source/Art/verify_bays.py       # checks the station art against the C#
python3 Source/Art/verify_brush.py      # checks the brush geometry against the C#
python3 Source/Art/make_about_art.py    # store page art, from the above
```

All four are run from the repo root.

## Why it is drawn rather than generated

The mending mod's art README works through this at length for its repair centre and the
conclusion holds here. Generators produce RENDERED machines - photoreal metal, fine
bevels, a heavy black outline of their own - and RimWorld's are ABSTRACT: a handful of
plain rounded blocks, flat tonal ramps, and detail only as a row of identical marks.
Prompting can get the subject right but not the drawing.

For the drone specifically there is a second problem. A Riimba is a disc, and a
generated disc comes back as an ellipse at some arbitrary aspect ratio with its
highlight in whatever place the model felt like. Three views of one object have to
agree about where the sensor is and which way the light falls, and nothing enforces
that across three separate generations.

## Depth is tone, not outline

Pure black appears only on the outer silhouette. Everything inside is a tone step:

* The drone's shell is three concentric discs, each lighter and each offset a few
  pixels UP. The dark crescent that leaves along the bottom edge is the entire shading
  model. A fourth disc starts to look like a rendered sphere, which is the wrong
  register for this game's top-down art.
* The station's case is a dark slab, a mid slab inset and stopped short of the bottom,
  and a lit slab across the top 42% of the SHORT side. Proportional to the short side,
  not the canvas: on the 192x576 east texture, using the canvas height put a light band
  across the top 240px that read as two materials bolted together.

One saturated colour, the teal, and it only ever marks something powered - the drone's
sensor, its pilot lamp, the station's subcore window and the bay lamps. Everything else
is desaturated grey so a Riimba reads as machinery beside RimWorld's warm-toned
colonists instead of competing with them.

## Rotations are views, not rotations

RimWorld's camera never turns, so `_north`, `_east` and `_south` are three views of the
same object. Turning the south sprite 180 degrees would move the sensor to the far side
of the disc but also light it from below, which reads as a hole rather than a bump.

`_west` is never drawn for either thing. `Graphic_Multi` mirrors `_east` horizontally
for west, and that is correct for both: the drone is symmetric about that axis, and
mirroring moves the station's bays from the right edge to the left, which is where
west's `FacingCell` of `(-1, 0, 0)` puts them.

## The station is 3x2 and its bays are inside it

The three bays are the station's own front row, not the row of floor outside it. A unit drives
onto one of the building's cells to dock.

That is what makes the overhang possible. `RiimbaStationLip_*.png` is the band where the
machine protrudes over its bays, drawn a second time by `Building_RiimbaStation` above pawn
altitude, so a unit reversing in passes under it. Because the bays are inside the footprint,
that mask only ever covers cells belonging to the building - not the open walkway in front of
it. It still clips any colonist who stands on a bay, which is the accepted cost; the band is
only as deep as it needs to be to hide the back of a 1.1-cell disc parked on the bay's centre.

The lip texture is the same size as the station's own, so both draw at the same rect and
cannot drift apart. `verify_bays.py` checks it exists, matches that size, and is not blank.

## The station's bays are a contract with the C#

`RiimbaSpots.BayCells` returns the row of cells just outside `rot.FacingCell`, and
`Building_RiimbaStation` sends each unit to the bay matching its roster position. So
the art has to put a bay where the code puts one, in every rotation:

| rotation | facing | bays drawn on | canvas |
| --- | --- | --- | --- |
| north | `(0, 1)` | top row | 576x384 |
| east | `(1, 0)` | right column | 384x576 |
| south | `(0, -1)` | bottom row | 576x384 |
| west | `(-1, 0)` | left column, by mirroring east | - |

Note the inversion on the horizontal pair: map z runs UP and screen y runs DOWN, so
north is the TOP of the texture. That is exactly the sign error that shipped in the
mending mod's east texture, where the item port landed on the cell the C# reads as the
output, and nobody caught it by looking.

So it is not checked by looking. `verify_bays.py` reimplements `BayCells` from the C#,
runs it for all four rotations, translates each cell into a pixel position in whichever
texture that rotation draws, and asserts the gold charging-contact colour is there and
is NOT on the opposite edge. It exits non-zero on a mismatch. Run it after any change
to either side:

```sh
python3 Source/Art/verify_bays.py
```

The contacts are used as the marker rather than the bay recess because that gold is the
only colour that appears nowhere else on the building; the recess tone is close enough
to the chassis shadow to give false positives.

## The drone is four layers, not three views

It turns to any heading now, so it cannot be three fixed sprites. It is split by what each
part does when the machine turns:

| layer | turns? | drawn | why |
| --- | --- | --- | --- |
| `RiimbaShell` | never | by the pawn renderer | the disc is symmetric, so holding it still keeps its highlight lit from the top of the screen at every heading |
| `RiimbaUnder` | with the heading | below the shell | wheels turn with the machine |
| `RiimbaFace` | with the heading | above the shell | bumper, sensor, lamp, vents - everything that says which way it points |
| `RiimbaBrush` | with the heading, and on its own axis | below the shell | the hub is carried round; the spinner also turns while cleaning |

Rotating the whole sprite instead would rotate its lighting with it, which is the thing this
file argues against everywhere else. Splitting it means only the parts that genuinely have an
orientation ever turn.

The rotating layers are authored pointing NORTH - front at the TOP of the texture - because
that is what `Graphic.Draw`'s `extraRotation` expects, the same convention vanilla projectiles
use, and `IntVec3.AngleFlat` gives 0 for north. So the heading feeds straight in with no sign
correction, which is exactly the kind of conversion that goes wrong unnoticed.

`verify_brush.py` checks the shell really is symmetric by rotating it 90, 180 and 270 degrees
and comparing: it currently differs from itself by 0.4-0.5%, against a 3% limit. Put a vent or
an off-centre highlight on the shell and that check fails, because the machine would then read
as having a fixed front that its own bumper slides around.

## The side brush is a separate sprite

The brush spins while a unit is working, so it cannot be painted into the body the way
everything else is. `riimba_unit.py` writes it to its own `RiimbaBrush.png` and the body
sprites are drawn without it; `CompRiimbaUnit.PostDraw` then draws it UNDER the body at a
per-facing offset and turns it a few degrees per tick.

Under, because the brush is mounted on the underside of the disc: only the part that
reaches past the rim should show, and the shell should hide the rest. It shipped drawing
on top for one commit, where it read as a spinner sitting on the lid.

Two details make that work:

* **The hub is dead centre of its own canvas.** The C# rotates that quad about its middle,
  so a hub drawn off-centre would make the brush orbit a point beside itself rather than
  turn on the spot.
* **The canvas is a 64px crop at the body's 256px scale**, not a 64px sprite blown up to
  fill the frame. That is what keeps the brush the same size it was when it was painted in:
  its draw size is `64/256 x 1.1` cells.

The offset is described in the def as `brushAlong` and `brushOut` - sideways and forwards
from the disc's centre, in cells - and resolved against the facing in
`CompRiimbaUnit.BrushOffset`, with west mirroring east in x because `Graphic_Multi` mirrors
the east body sprite for west. `riimba_unit.py` prints all four offsets whenever it
regenerates the textures.

That is a number living in two places, so `verify_brush.py` checks they agree: it reads the
def, recomputes the offsets from the art script's own `BRUSH_ALONG` / `BRUSH_OUT`, and
composites the brush under each body sprite and measures how much of it still reaches past
the shell - a shade under 78% in every rotation. The band it allows is 50% to 95%, which is
narrow in both directions on purpose: near 100% means the brush has drifted off the machine,
far below means it has slid under the disc and nothing visibly turns. The over-the-top bug
scores exactly 100%, so this check now fails it. This was checked once by hand against the sprites from before the split,
and the recomposited image is pixel-identical to the old baked-in one apart from resampling
inside the brush's own footprint.

Drawing it from a comp rather than giving Riimba its own `PawnRenderTreeDef` is deliberate:
`Pawn.DrawAt` calls `Comps_PostDraw`, so a comp can draw on a pawn without restating the
body, wound and carried-thing nodes of a render tree and re-checking them against every
future version, all to hang one spinning quad off the machine.

## Supersampling

`riimba_draw.py` draws everything at 4x and reduces with LANCZOS. PIL's `ellipse` and
`polygon` are hard-aliased, and a 96px disc drawn directly has a visible staircase on
its rim at RimWorld's default zoom. 4x is where further increases stop being visible
after the downsample.

## Sizes

| texture | size | why |
| --- | --- | --- |
| `RiimbaShell.png` | 256x256 | the body graphic, drawn at `drawSize 1.1`, never rotated |
| `RiimbaUnder.png`, `RiimbaFace.png` | 256x256 | the rotating layers, authored pointing north |
| `RiimbaBrush.png` | 64x64 | the spinner alone, hub centred, cropped at the body's scale |
| `RiimbaStationLip_*.png` | as the station | the overhang, drawn above pawns as a mask |
| `RiimbaStation_north/south.png` | 576x192 | 3x1 footprint at 192px per cell, exact |
| `RiimbaStation_east.png` | 192x576 | the same, axes swapped |
| `About/Preview.png` | 640x360 | what the workshop shows |
| `About/ModIcon.png` | 256x256 | shown at about 32px in the mod list |

The station draws at `drawSize (3,1)`, equal to its `size`, so the art lands inside its
own cells with no overhang - the same choice the mending benches make, and unlike the
repair centre, which deliberately overhangs by half a cell to match the factory
machines it sits beside.

`make_about_art.py` composites the store art out of the real shipped textures rather
than drawing its own, so the store page cannot drift from what is in the game. The icon
is the drone alone: at 32px a station with three bays on it is an indistinct grey bar,
while a dark disc with one teal eye still reads.

## Scripts

| script | builds |
| --- | --- |
| `riimba_draw.py` | shared primitives, the palette, and the supersampling |
| `riimba_unit.py` | the drone's four layers |
| `riimba_station.py` | the station, north/east/south |
| `verify_bays.py` | checks the station textures against `RiimbaSpots.BayCells` |
| `verify_brush.py` | checks the layer offsets, shell symmetry and brush tuck |
| `make_about_art.py` | `About/Preview.png` and `About/ModIcon.png` |
