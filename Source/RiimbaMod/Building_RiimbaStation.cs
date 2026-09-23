using System.Collections.Generic;
using System.Text;
using RimWorld;
using UnityEngine;
using Verse;

namespace RiimbaMod
{
    // The thing that makes a Riimba more than a mech: it holds the roster, it draws the boundary
    // the units work inside, it charges them, and it takes what they collect.
    //
    // There is no AI here. The units ask this building questions - am I signed on, is my bay
    // free, is that mess inside your radius - and the answers come from plain state. Keeping the
    // decisions in the units' think tree and the facts in the station is what stops the two
    // drifting apart.
    public class Building_RiimbaStation : Building
    {
        // Saved as references, so a unit that is destroyed while the game is not loaded comes
        // back as null and is cleaned out on the next tick rather than resurrecting a dead entry.
        private List<Pawn> units = new List<Pawn>();

        private static readonly Vector2 LipDrawSize = new Vector2(3f, 2f);

        private Graphic lipGraphic;
        private CompPowerTrader power;
        private CompRiimbaWasteBuffer wasteBuffer;
        private RiimbaStationExtension extension;

        // The player's setting for this station, or negative for "never touched, use the def's".
        // Storing the sentinel rather than copying the def's value in at build time means an
        // existing save picks up a changed default, and a station the player HAS adjusted keeps
        // the number they chose.
        private float commandRadius = -1f;

        private RiimbaStationExtension Extension =>
            extension ?? (extension = def.GetModExtension<RiimbaStationExtension>() ?? new RiimbaStationExtension());

        public CompPowerTrader Power => power ?? (power = GetComp<CompPowerTrader>());

        public CompRiimbaWasteBuffer WasteBuffer =>
            wasteBuffer ?? (wasteBuffer = GetComp<CompRiimbaWasteBuffer>());

        // A station with no power comp at all still counts as powered, so the def can drop the
        // comp for a debug or no-power variant without the whole building going inert.
        public bool PowerOn => Power == null || Power.PowerOn;

        public int MaxUnits => Extension.maxUnits;

        public float MinRadius => Extension.minRadius;

        // A linked signal relay raises the ceiling; the floor never moves.
        public float MaxRadius => Mathf.Max(Extension.minRadius, Extension.maxRadius + RadiusBonus);

        // Both read as stats, which is how vanilla facilities feed a building: CompFacility
        // statOffsets land on it through CompAffectedByFacilities.GetStatOffset, and the stat's
        // own explanation lists which facility contributed what, for free.
        public float RadiusBonus => Mathf.Max(0f, this.GetStatValue(RiimbaDefOf.RiimbaRadiusBonus));

        public float ChargeSpeed => Mathf.Max(0.1f, this.GetStatValue(RiimbaDefOf.RiimbaChargeSpeed));

        // The first active hopper linked to this station, if any. Only spawned, active ones: a
        // hopper that has been uninstalled is still briefly in the link list, and dropping waste
        // at the position of something in a crate would put it on the floor where it used to be.
        public Thing LinkedHopper
        {
            get
            {
                CompAffectedByFacilities facilities = GetComp<CompAffectedByFacilities>();
                if (facilities == null)
                    return null;

                List<Thing> linked = facilities.LinkedFacilitiesListForReading;
                for (int i = 0; i < linked.Count; i++)
                {
                    Thing facility = linked[i];
                    if (facility.def == RiimbaDefOf.RiimbaWasteHopper && facility.Spawned
                        && facilities.IsFacilityActive(facility))
                        return facility;
                }

                return null;
            }
        }

        // Clamped on the way out rather than only on the way in, so a save written when the def
        // allowed a bigger ring - a settings change, a mod update - comes back inside the range
        // the def allows now instead of keeping a value the slider can no longer produce.
        public float Radius => Mathf.Clamp(commandRadius < 0f ? Extension.radius : commandRadius,
            MinRadius, MaxRadius);

        public void SetRadius(float value)
        {
            commandRadius = Mathf.Clamp(value, MinRadius, MaxRadius);

            // The draw changes the moment the ring does, rather than at the next tick: a player
            // who has just dragged the slider is looking straight at the power figure.
            UpdatePowerDraw();
        }

        // What a given ring costs to broadcast. Public because the slider quotes it live while
        // the player drags, which is the whole point of charging for reach: the trade has to be
        // visible at the moment the choice is made, not discovered later in the power tab.
        public float PowerForRadius(float radius)
        {
            if (!RiimbaModMain.Settings.enforceRadius)
                return 0f;

            float covered = Mathf.PI * (radius * radius - MinRadius * MinRadius);
            return Mathf.Max(0f, covered * Extension.powerPerCoveredTile);
        }

        public bool HasFreeSlot => units.Count < MaxUnits;

        public List<Pawn> Units => units;

        private CellRect Footprint => this.OccupiedRect();

        public List<IntVec3> BayCells => RiimbaSpots.BayCells(Footprint, Rotation);

        public IntVec3 WasteOutputCell => RiimbaSpots.WasteOutputCell(Footprint, Rotation);

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Collections.Look(ref units, "units", LookMode.Reference);
            Scribe_Values.Look(ref commandRadius, "commandRadius", -1f);

            if (Scribe.mode == LoadSaveMode.PostLoadInit && units == null)
                units = new List<Pawn>();
        }

        // Uninstalling or destroying the station has to release its units, or they stay pointing
        // at a building inside a minified crate: CompRiimbaUnit would see a despawned station,
        // and the unit would sit idle forever holding a slot on something that no longer exists.
        public override void DeSpawn(DestroyMode mode = DestroyMode.Vanish)
        {
            for (int i = units.Count - 1; i >= 0; i--)
                units[i]?.GetComp<CompRiimbaUnit>()?.ClearStation();

            units.Clear();

            base.DeSpawn(mode);
        }

        public bool InRadius(IntVec3 cell)
        {
            if (!RiimbaModMain.Settings.enforceRadius)
                return true;

            // Measured from the centre of the footprint, which is what the placement ring and the
            // selection ring both draw.
            return cell.InHorDistOf(Footprint.CenterCell, Radius);
        }

        public bool IsUnitSignedOn(Pawn unit)
        {
            return unit != null && units.Contains(unit);
        }

        public void Notify_UnitSignedOn(Pawn unit)
        {
            if (unit == null || units.Contains(unit))
                return;

            // Guarded here as well as at every call site: this is the one place that can be sure
            // the roster is not about to go over strength.
            if (units.Count >= MaxUnits)
                return;

            units.Add(unit);
        }

        public void Notify_UnitSignedOff(Pawn unit)
        {
            units.Remove(unit);
        }

        // Which bay a given unit owns, by roster position rather than by "first free cell".
        //
        // Position, not identity: signing a unit off shifts everyone behind it down one, so the
        // others may end up on a different bay than before. That is fine and it is why bays are
        // not reserved - what matters is only that no two units are ever sent to the SAME bay,
        // which indexing a shared list guarantees by construction. A "first free cell" search
        // would not: two units deciding to dock on the same tick would both see the same cell
        // free and both drive to it.
        public IntVec3 BayCellFor(Pawn unit)
        {
            int index = units.IndexOf(unit);
            List<IntVec3> bays = BayCells;

            if (index < 0 || bays.Count == 0)
                return IntVec3.Invalid;

            return bays[index % bays.Count];
        }

        public bool IsUnitOnBay(Pawn unit)
        {
            IntVec3 bay = BayCellFor(unit);
            return bay.IsValid && unit != null && unit.Spawned && unit.Position == bay;
        }

        protected override void Tick()
        {
            base.Tick();

            // Once a second is plenty for roster hygiene and power bookkeeping, and avoids
            // walking the unit list sixty times a second to learn nothing.
            if (!this.IsHashIntervalTick(60))
                return;

            PruneUnits();
            UpdatePowerDraw();
        }

        // Entries go stale in ways no notification covers: a unit killed on another map, one
        // destroyed while this station was itself despawned, or a save loaded after the unit's
        // def was removed by a mod change. A null or dead entry would otherwise hold a slot
        // forever and quietly cap the station below its own maximum.
        private void PruneUnits()
        {
            for (int i = units.Count - 1; i >= 0; i--)
            {
                Pawn unit = units[i];

                if (unit == null || unit.Destroyed || unit.Dead)
                {
                    units.RemoveAt(i);
                    continue;
                }

                // A unit that has wandered onto another map is not this station's to command.
                if (unit.Spawned && unit.Map != Map)
                {
                    units.RemoveAt(i);
                    unit.GetComp<CompRiimbaUnit>()?.ClearStation();
                }
            }
        }

        // Charging costs real power, so a station with three units on its bays draws far more
        // than an idle one, and so does a wide command radius. Without this the building would
        // cost the same whether it was doing anything or not, which is the kind of free lunch
        // that makes automation a no-brainer.
        private void UpdatePowerDraw()
        {
            if (Power == null)
                return;

            int charging = 0;
            foreach (Pawn unit in units)
            {
                if (unit != null && IsUnitOnBay(unit))
                {
                    CompRiimbaUnit comp = unit.GetComp<CompRiimbaUnit>();
                    if (comp != null && comp.Charge < 1f)
                        charging++;
                }
            }

            // Charge speed scales the draw with it. A fast-charge pad makes charging quicker, not
            // cheaper: the same energy goes into the unit, in less time, at more watts.
            Power.PowerOutput = -(Power.Props.PowerConsumption
                + PowerForRadius(Radius)
                + charging * Extension.powerPerChargingUnit * ChargeSpeed);
        }

        // The overhang, drawn a second time above pawn altitude so a unit reversing into a bay
        // passes UNDER it. The station's own sprite already contains this band; this is the same
        // pixels again, on top, acting as a mask.
        //
        // Built through GraphicDatabase with the same drawSize as the building so it uses the
        // building's own mesh and rotation handling - reconstructing the quad by hand would mean
        // reimplementing how Graphic_Multi swaps the axes for the east and west rotations, and
        // getting that subtly wrong is a misalignment nobody would spot until a unit docked.
        private Graphic LipGraphic
        {
            get
            {
                if (lipGraphic == null)
                {
                    lipGraphic = GraphicDatabase.Get<Graphic_Multi>(
                        LipTexPath, ShaderDatabase.Cutout, LipDrawSize, Color.white);
                }

                return lipGraphic;
            }
        }

        private string LipTexPath => def.graphicData.texPath + "Lip";

        // Only reached because the def sets drawerType to MapMeshAndRealTime. BuildingBase is
        // MapMeshOnly, and Thing.DynamicDrawPhase does not call DrawAt on a MapMeshOnly thing at
        // all - so with the inherited value this method is dead code and the overhang never
        // appears, with nothing logged to say why. RiimbaDefPatches re-checks it on startup.
        protected override void DrawAt(Vector3 drawLoc, bool flip = false)
        {
            // Draws nothing of the chassis: Thing.DrawAt draws the graphic only when drawerType is
            // RealtimeOnly, and ours is printed into the map mesh. It is still called for the
            // silhouette handling that lives in there.
            base.DrawAt(drawLoc, flip);

            Graphic lip = LipGraphic;
            if (lip == null)
                return;

            // PawnState sits one layer above Pawn, so this covers a docked unit. It also covers
            // any colonist standing on a bay, which is the accepted cost of the effect: the strip
            // is only as deep as it needs to be, and it lies inside the machine's own footprint
            // rather than across the walkway in front of it.
            Vector3 loc = drawLoc;
            loc.y = AltitudeLayer.PawnState.AltitudeFor();

            lip.Draw(loc, Rotation, this);
        }

        public override void DrawExtraSelectionOverlays()
        {
            base.DrawExtraSelectionOverlays();

            if (Map == null)
                return;

            // The same rings the place worker draws, so a built station and one on the cursor
            // mark themselves identically.
            RiimbaSpots.DrawSpots(Footprint, Rotation, RiimbaModMain.Settings.enforceRadius ? Radius : 0f);
        }

        public override IEnumerable<Gizmo> GetGizmos()
        {
            foreach (Gizmo gizmo in base.GetGizmos())
                yield return gizmo;

            if (Faction != Faction.OfPlayer)
                yield break;

            Command_RiimbaRadius command = new Command_RiimbaRadius
            {
                station = this,
                defaultLabel = "Riimba.SetRadiusLabel".Translate(),
                defaultDesc = "Riimba.SetRadiusDesc".Translate(),
                icon = RiimbaTextures.SetRadius,
            };

            // The ring does nothing when the leash is switched off in the mod settings, and it
            // costs nothing either - so the command says so rather than quietly setting a number
            // that has no effect on anything.
            if (!RiimbaModMain.Settings.enforceRadius)
                command.Disable("Riimba.SetRadiusDisabled".Translate());

            yield return command;
        }

        public override string GetInspectString()
        {
            StringBuilder sb = new StringBuilder(base.GetInspectString());

            if (sb.Length > 0)
                sb.AppendLine();

            if (!PowerOn)
            {
                sb.Append("Riimba.StationNoPower".Translate());
            }
            else
            {
                sb.Append("Riimba.StationUnits".Translate(units.Count, MaxUnits));

                if (RiimbaModMain.Settings.enforceRadius)
                {
                    sb.AppendLine();
                    sb.Append("Riimba.StationRadius".Translate(
                        Radius.ToString("F0"), PowerForRadius(Radius).ToString("F0")));
                }

                int docked = 0;
                foreach (Pawn unit in units)
                {
                    if (unit != null && IsUnitOnBay(unit))
                        docked++;
                }

                if (docked > 0)
                {
                    sb.AppendLine();
                    sb.Append("Riimba.StationDocked".Translate(docked));
                }
            }

            sb.AppendLine();
            sb.Append("Riimba.StationLegend".Translate());

            return sb.ToString();
        }
    }
}
