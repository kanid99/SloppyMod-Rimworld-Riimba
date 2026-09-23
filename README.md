# SloppyMods Riimba

A semi-autonomous cleaning drone for RimWorld 1.6. Gestated at a mech gestator like any
light mech, but driven by a control station rather than by a mechanitor: one station
commands up to three units inside a radius you set - six to thirty tiles, paid for in power -
charges them at its docking bays, and takes the waste they collect.

## Installing

This repository IS the mod, so it can be cloned straight into your mods folder:

```sh
git clone https://github.com/kanid99/SloppyMod-Rimworld-Riimba.git "RimWorld/Mods/Riimba"
```

Then build the assemblies (below) and enable it in the mod list. A release copy needs only:

```
Riimba/
    About/
    Assemblies/
    Defs/
    Languages/
    LoadFolders.xml
    Mods/TrashChute/     the optional trash chute - see below
    Textures/
```

`Source/` does not need to ship.

Riimba began life in the `Riimba/` folder of the SloppyMods Mending Solutions repository
and was split out with `git subtree split`, so the history here is its own from the first
commit. The two mods share no code and neither depends on the other.

## Requirements

* **Biotech** - the mech gestator the drones are built at, and the basic subcore the
  station is built around.
* **Vanilla Recycling Expanded** - supplies the trash the units produce. Without it the
  station falls back to putting everything out as wastepacks; the def names it looks for
  are XML-tunable in `Defs/ThingDefs_Buildings/Buildings_RiimbaStation.xml`.

## Building the assemblies

```sh
dotnet build Source/RiimbaMod/RiimbaMod.csproj
dotnet build Source/RiimbaChute/RiimbaChute.csproj -p:PipeSystemDll="<path to>/PipeSystem.dll"
```

Output goes to `Assemblies/` and `Mods/TrashChute/Assemblies/`, both gitignored.

The second is the trash chute, and it is a separate assembly on purpose: it is built on
Vanilla Expanded Framework's pipe system, and a reference to that from `RiimbaMod` would stop
the whole mod loading for anyone without the framework. `LoadFolders.xml` loads
`Mods/TrashChute` only when Vanilla Recycling Expanded and the framework are both active, and
the chute plugs itself into the main assembly at startup through `RiimbaWasteRouting`.
`PipeSystem.dll` is not redistributable and not on NuGet; it defaults to the framework's
Steam Workshop install, and Vanilla Recycling Expanded's own source ships a reference copy
that works just as well.

The project finds RimWorld's types one of two ways, and picks on its own:

* **On a machine with the game installed**, it references the DLLs in RimWorld's `Managed`
  folder - the real assemblies from the install being modded. Point it at a non-default
  install with `-p:RimWorldManagedDir="<path to>/RimWorldWin64_Data/Managed"`.
* **Otherwise** it falls back to [`Krafs.Rimworld.Ref`](https://www.nuget.org/packages/Krafs.Rimworld.Ref),
  reference assemblies for RimWorld published on NuGet. They carry the public API with method
  bodies stripped, which is enough to compile against and is redistributable in a way the
  game's own DLLs are not.

That second path is the point: it means this builds in CI, in a container, or on any machine
without RimWorld, so a change can be verified to compile by someone other than the author.
Force either with `-p:UseLocalRimWorldRefs=true` or `=false`. Keep `RimWorldRefVersion` in the
csproj in step with the game version in `About.xml`.

## How it fits together

| piece | what it does |
| --- | --- |
| `Riimba` (pawn) | mechanoid, no `CompOverseerSubject`, custom think tree |
| `RiimbaStation` (building) | roster of up to 3, adjustable radius, docking bays, waste buffer |
| `Riimba_Gestate` (recipe) | mech gestator bill - a mechanitor runs it, as with any mech |
| `RiimbaCleaning` (research) | behind Basic Mechtech and Fabrication |
| `RiimbaFastChargePad` | facility: +50% charge speed per pad, two per station, more watts while charging |
| `RiimbaSignalRelay` | facility: +10 tiles on the radius slider's ceiling, one per station |
| `RiimbaWasteHopper` | facility: storage the station puts its waste into instead of its spot |
| `RiimbaTrashChute` | pipe carrying trash from stations to a garbage compactor or an outlet |
| `RiimbaTrashChuteHidden` | the same chute laid under the floor: invisible once built, shown in the chute overlay, dearer and slower to lay |
| `RiimbaChuteOutlet` | end of a chute that puts trash back out as items, for haulers or belts |

Each unit also has its own allowed area, chosen from the player's areas, which limits the
messes it takes without limiting where it drives - it can always reach its bay. With room
priority on, hospitals are cleaned first and kitchens second. Alerts flag a unit that has run
flat, a unit with no station, and a station that has lost power with units on it.

The drone is a mech so that gestation, pathing, damage, reservations and the cleaning
job all come for free, but `RiimbaDefPatches` strips `CompOverseerSubject` from its def
at startup. That single comp is what vanilla hangs all mechanitor control off
(`MechanitorUtility.EverControllable` is `mech.OverseerSubject != null`), so removing it
takes the unit out of control groups, out of the bandwidth tally and out of the "went
feral without an overseer" machinery in one stroke - leaving the station as the only
thing that commands it.

Design notes live next to the code they explain. The art pipeline has its own writeup in
[`Source/Art/README.md`](Source/Art/README.md).

## Settings

Waste on/off and amount, where trash goes (the output spot or a linked hopper, or the trash
chute), charge drain rate (zero for units that never need to dock), whether hospitals and
kitchens are cleaned first, and whether the station's radius is enforced at all - with it
off, units work anywhere they can reach and the radius costs no power, since it is no longer
holding anything in.
