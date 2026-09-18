using System.Collections.Generic;
using System.Text;
using RimWorld;
using UnityEngine;
using Verse;

namespace RiimbaMod
{
    public class CompProperties_RiimbaUnit : CompProperties
    {
        // Charge is a 0..1 fraction, and these are fractions per in-game day.
        public float chargeFallPerDayWorking = 0.40f;
        public float chargeFallPerDayIdle = 0.10f;
        public float chargeGainPerDayDocked = 6.0f;

        // Below this, the unit stops what it is doing and goes home.
        public float returnChargeFraction = 0.25f;

        // Units of collected filth the bin holds before a trip back is needed. One unit is one
        // waste item at the station's default threshold.
        public float binCapacity = 6.0f;

        // The side brush is drawn separately from the body and spun while the unit works, so
        // its position has to be described here rather than baked into the body sprite.
        //
        // along/out are the hub's offset from the disc's centre in cells, resolved against the
        // facing: "out" is towards the front, "along" is sideways. Both come straight out of
        // Source/Art/riimba_unit.py, which prints them when it regenerates the textures, and
        // verify_brush.py fails the build if the two ever disagree.
        public string brushTexPath = "Things/Pawn/Riimba/RiimbaBrush";
        public float brushAlong = 0.198f;
        public float brushOut = 0.3841f;
        public float brushDrawSize = 0.275f;

        // About one turn every two seconds at normal speed. Fast enough to read as spinning,
        // slow enough not to strobe against the 60-tick second.
        public float brushDegreesPerTick = 3.0f;

        public CompProperties_RiimbaUnit()
        {
            compClass = typeof(CompRiimbaUnit);
        }
    }

    // Everything that makes a Riimba a Riimba rather than a small mech: which station commands
    // it, how much charge it has left, and what is in its bin.
    public class CompRiimbaUnit : ThingComp
    {
        private const int TicksPerDay = 60000;

        // A floor under HasChargeToWork, as a fraction of the return threshold.
        //
        // In normal running this never bites: the dock node sits above the cleaning node in the
        // think tree and fires at returnChargeFraction, so a unit stops working long before it
        // gets near this. It is for the case where docking is impossible anyway - a bay walled
        // off, the station out of reach - where the unit may as well go on cleaning rather than
        // stand still, but should still stop short of running itself completely flat.
        private const float ReserveChargeFraction = 0.05f;

        private Building_RiimbaStation station;
        private float charge = 1f;
        private float trashLoad;
        private float bioLoad;

        // The gestator hands the finished mech to the mechanitor who ran the bill, as an Overseer
        // relation (Bill_ProductionMech.CreateProducts). A Riimba is not theirs to command, so the
        // relation is dropped - but not before the release job that spawned it has finished, which
        // is why this happens on the first tick rather than in PostSpawnSetup.
        private bool overseerRelationChecked;

        // Not saved. It is a drawing detail with no bearing on anything, and a brush that
        // resumes from a different angle after a reload is not something anyone can notice.
        private float brushAngle;
        private Material brushMaterial;

        public CompProperties_RiimbaUnit Props => (CompProperties_RiimbaUnit)props;

        public Pawn Unit => (Pawn)parent;

        public Building_RiimbaStation Station => station;

        public float Charge => charge;

        public float BinFraction => Props.binCapacity > 0f
            ? Mathf.Clamp01((trashLoad + bioLoad) / Props.binCapacity)
            : 0f;

        public bool BinFull => trashLoad + bioLoad >= Props.binCapacity;

        public bool BinEmpty => trashLoad + bioLoad <= 0f;

        public bool NeedsCharge => charge <= Props.returnChargeFraction;

        // Flat, and going nowhere under its own power. Kept separate from NeedsCharge because the
        // two want different answers: one sends the unit home, the other stops it moving at all.
        public bool OutOfCharge => charge <= 0f;

        public bool CanWorkNow
        {
            get
            {
                if (station == null || !station.Spawned || !station.PowerOn)
                    return false;

                return !OutOfCharge && !BinFull && !Unit.Downed && !Unit.Dead;
            }
        }

        public override void PostExposeData()
        {
            base.PostExposeData();
            Scribe_References.Look(ref station, "station");
            Scribe_Values.Look(ref charge, "charge", 1f);
            Scribe_Values.Look(ref trashLoad, "trashLoad", 0f);
            Scribe_Values.Look(ref bioLoad, "bioLoad", 0f);
            Scribe_Values.Look(ref overseerRelationChecked, "overseerRelationChecked", false);
        }

        // CompTickInterval rather than CompTick: 1.6 calls it with the number of ticks that have
        // actually elapsed, which is exactly the shape charge accounting wants, and it runs at the
        // pawn's throttled rate instead of 60 times a second for arithmetic nobody can see.
        public override void CompTickInterval(int delta)
        {
            base.CompTickInterval(delta);

            if (!overseerRelationChecked)
            {
                overseerRelationChecked = true;
                DropOverseerRelation();
            }

            if (!parent.Spawned)
                return;

            if (station != null && (!station.Spawned || station.Destroyed))
            {
                // The station was destroyed or uninstalled out from under it. Sign off rather
                // than hold a reference to a building that is gone; the seek-station node will
                // find another one if the player builds it.
                station = null;
            }

            // Driven off ticks rather than frame time so it stops dead when the game is paused
            // and speeds up with the game speed, which is how every other moving thing on the
            // map behaves.
            if (IsBrushSpinning)
                brushAngle = (brushAngle + Props.brushDegreesPerTick * delta) % 360f;

            if (IsDockedAndCharging)
                GainCharge(delta, Props.chargeGainPerDayDocked);
            else if (IsOnTrickle)
                GainCharge(delta, Props.chargeGainPerDayDocked * TrickleRateFraction);
            else
                DrainCharge(delta);
        }

        private bool IsDockedAndCharging => station != null
            && station.Spawned
            && station.PowerOn
            && station.IsUnitOnBay(Unit);

        // The failsafe that stops a flat unit becoming litter. A unit that runs out on the far
        // side of a room cannot drive to a bay, and nothing else in the game can push it there -
        // a pawn cannot haul a pawn. So a powered station induction-charges any of its own units
        // that are lying flat, slowly, which is enough to get one moving again.
        //
        // Only ever applies at zero: otherwise it would be a free trickle that made the docking
        // bays pointless, which is the opposite of what the station is for.
        //
        // Deliberately NOT restricted to the station's radius. A unit can end up outside it -
        // pathing to a mess near the edge can route around a wall - and a flat unit outside the
        // radius with no trickle is unrecoverable, permanently. The radius governs where a unit
        // WORKS; it should not decide whether one can ever be revived.
        private bool IsOnTrickle => OutOfCharge
            && station != null
            && station.Spawned
            && station.Map == parent.Map
            && station.PowerOn;

        // Deliberately slow. Recovering from flat should be a visible inconvenience, not a
        // shrug - a unit that ran itself down takes most of an hour to get going again.
        private const float TrickleRateFraction = 0.04f;

        private void GainCharge(int delta, float perDay)
        {
            charge = Mathf.Clamp01(charge + perDay * delta / TicksPerDay);
        }

        private void DrainCharge(int delta)
        {
            float multiplier = RiimbaModMain.Settings.chargeDrainMultiplier;
            if (multiplier <= 0f)
                return;

            // "Working" is judged by the job it is actually running, not by whether it has a
            // station: a unit standing idle in a powered room should not burn charge at the same
            // rate as one scrubbing a floor.
            bool working = Unit.CurJobDef == RiimbaDefOf.Riimba_Clean;
            float perDay = working ? Props.chargeFallPerDayWorking : Props.chargeFallPerDayIdle;

            charge = Mathf.Clamp01(charge - perDay * multiplier * delta / TicksPerDay);
        }

        // Called by the cleaning job as each unit of thickness comes off a mess. Returns how much
        // was actually taken, so the caller can stop when the bin is full mid-puddle.
        public float AddCollected(ThingDef filthDef, float amount)
        {
            if (!RiimbaModMain.Settings.generateWaste || amount <= 0f)
                return 0f;

            amount *= RiimbaModMain.Settings.wasteMultiplier;
            if (amount <= 0f)
                return 0f;

            float room = Mathf.Max(0f, Props.binCapacity - (trashLoad + bioLoad));
            float taken = Mathf.Min(room, amount);
            if (taken <= 0f)
                return 0f;

            if (RiimbaFilth.IsBiological(filthDef))
                bioLoad += taken;
            else
                trashLoad += taken;

            return taken;
        }

        // Hands the bin to the station and empties it. Anything the station cannot take stays in
        // the bin rather than evaporating, so a station with nowhere to put its waste backs the
        // units up instead of quietly deleting what they collected.
        public void EmptyBinInto(CompRiimbaWasteBuffer buffer)
        {
            if (buffer == null)
                return;

            trashLoad -= buffer.AcceptWaste(trashLoad, biological: false);
            bioLoad -= buffer.AcceptWaste(bioLoad, biological: true);

            trashLoad = Mathf.Max(0f, trashLoad);
            bioLoad = Mathf.Max(0f, bioLoad);
        }

        // Charge the unit will not spend on cleaning, so it always has enough left to drive home.
        public bool HasChargeToWork => charge > Props.returnChargeFraction * ReserveChargeFraction;

        // The station is the one that decides whether it has room, and this only records the
        // answer. Setting the field first and telling the station afterwards would let a unit
        // believe it was signed on to a station that had turned it away - it would drive to a
        // bay that belongs to someone else and charge off a slot it does not hold.
        public void AssignStation(Building_RiimbaStation newStation)
        {
            if (station == newStation)
                return;

            station?.Notify_UnitSignedOff(Unit);
            station = null;

            if (newStation == null)
                return;

            newStation.Notify_UnitSignedOn(Unit);

            if (newStation.IsUnitSignedOn(Unit))
                station = newStation;
        }

        public void ClearStation()
        {
            AssignStation(null);
        }

        public override void PostDeSpawn(Map map, DestroyMode mode)
        {
            base.PostDeSpawn(map, mode);
            station?.Notify_UnitSignedOff(Unit);
        }

        public override void PostDestroy(DestroyMode mode, Map previousMap)
        {
            base.PostDestroy(mode, previousMap);
            station?.Notify_UnitSignedOff(Unit);
            station = null;
        }

        // See the field comment. MechanitorUtility.GetOverseer reads the mech's own direct
        // relations - the Overseer relation def is reflexive, so it lands on both pawns - and
        // dropping it here takes the unit out of the mechanitor's overseen list entirely.
        private void DropOverseerRelation()
        {
            Pawn unit = Unit;
            if (unit?.relations == null)
                return;

            Pawn overseer = unit.GetOverseer();
            if (overseer == null)
                return;

            unit.relations.RemoveDirectRelation(PawnRelationDefOf.Overseer, overseer);
        }

        // The brush turns while the unit is on a cleaning job, which covers driving to the next
        // mess as well as scrubbing one - the goto is part of that job. Everything else, including
        // sitting on a bay, leaves it still.
        private bool IsBrushSpinning => parent.Spawned
            && !Unit.Dead
            && !Unit.Downed
            && Unit.CurJobDef == RiimbaDefOf.Riimba_Clean;

        private Material BrushMaterial
        {
            get
            {
                if (brushMaterial == null && !Props.brushTexPath.NullOrEmpty())
                    brushMaterial = MaterialPool.MatFrom(Props.brushTexPath, ShaderDatabase.Cutout);

                return brushMaterial;
            }
        }

        // The hub's offset from the pawn's centre for a given facing, built the same way
        // Source/Art/riimba_unit.py builds it: "out" towards the front, "along" to one side.
        //
        // West is the east offset mirrored in x, because Graphic_Multi draws west by flipping
        // the east body sprite - so the brush has to flip with it or it would swap sides.
        private Vector3 BrushOffset(Rot4 rotation)
        {
            float along = Props.brushAlong;
            float o = Props.brushOut;

            if (rotation == Rot4.South)
                return new Vector3(-along, 0f, -o);
            if (rotation == Rot4.North)
                return new Vector3(along, 0f, o);
            if (rotation == Rot4.East)
                return new Vector3(o, 0f, -along);

            return new Vector3(-o, 0f, -along);
        }

        // Pawn.DrawAt calls Comps_PostDraw, so a comp can draw on a pawn without replacing its
        // render tree. That matters here: the alternative was giving Riimba its own
        // PawnRenderTreeDef, which would mean restating the body, wound and carried-thing nodes
        // and re-checking them against every future version, all to hang one spinning quad off
        // the machine.
        public override void PostDraw()
        {
            base.PostDraw();

            Material material = BrushMaterial;
            if (material == null || !parent.Spawned)
                return;

            // A downed pawn is drawn lying down - the renderer turns the body ninety degrees -
            // so the offsets below, which assume an upright disc seen from above, would put the
            // brush somewhere beside the wreck. A downed unit simply shows no brush.
            if (Unit.Downed || Unit.Dead)
                return;

            Vector3 position = parent.DrawPos + BrushOffset(parent.Rotation);

            // One altitude increment above the body, so the brush sits on top of the shell
            // rather than z-fighting with it.
            position.y += Altitudes.AltInc;

            Matrix4x4 matrix = Matrix4x4.TRS(
                position,
                Quaternion.AngleAxis(brushAngle, Vector3.up),
                new Vector3(Props.brushDrawSize, 1f, Props.brushDrawSize));

            Graphics.DrawMesh(MeshPool.plane10, matrix, material, 0);
        }

        public override IEnumerable<Gizmo> CompGetGizmosExtra()
        {
            if (!parent.Spawned || parent.Faction != Faction.OfPlayer)
                yield break;

            yield return new Command_Action
            {
                defaultLabel = "Riimba.AssignStationLabel".Translate(),
                defaultDesc = "Riimba.AssignStationDesc".Translate(),
                icon = TexCommand.Install,
                action = BeginStationTargeting,
            };

            if (station != null)
            {
                yield return new Command_Action
                {
                    defaultLabel = "Riimba.SignOffLabel".Translate(),
                    defaultDesc = "Riimba.SignOffDesc".Translate(),
                    icon = TexCommand.ClearPrioritizedWork,
                    action = ClearStation,
                };
            }
        }

        // A targeter rather than a float menu: with several stations on a map, pointing at the one
        // you mean is quicker than reading a list of identical labels, and it shows the radius of
        // whatever is under the cursor while you choose.
        private void BeginStationTargeting()
        {
            TargetingParameters parameters = new TargetingParameters
            {
                canTargetBuildings = true,
                canTargetPawns = false,
                canTargetItems = false,
                mapObjectTargetsMustBeAutoAttackable = false,
                validator = target => target.Thing is Building_RiimbaStation,
            };

            Find.Targeter.BeginTargeting(parameters, target =>
            {
                if (!(target.Thing is Building_RiimbaStation chosen))
                    return;

                if (chosen == station)
                    return;

                if (!chosen.HasFreeSlot)
                {
                    Messages.Message(
                        "Riimba.StationFull".Translate(chosen.Label, chosen.MaxUnits),
                        chosen, MessageTypeDefOf.RejectInput, historical: false);
                    return;
                }

                AssignStation(chosen);
            });
        }

        public override string CompInspectStringExtra()
        {
            StringBuilder sb = new StringBuilder();

            sb.Append("Riimba.UnitCharge".Translate(charge.ToStringPercent()));

            if (RiimbaModMain.Settings.generateWaste)
            {
                sb.AppendLine();
                sb.Append("Riimba.UnitBin".Translate(BinFraction.ToStringPercent()));
            }

            sb.AppendLine();

            if (station == null)
            {
                sb.Append("Riimba.UnitNoStation".Translate());
            }
            else if (!station.PowerOn)
            {
                sb.Append("Riimba.UnitStationUnpowered".Translate());
            }
            else if (OutOfCharge)
            {
                sb.Append("Riimba.UnitFlat".Translate());
            }
            else
            {
                sb.Append("Riimba.UnitStation".Translate(station.Label));
            }

            return sb.ToString();
        }
    }
}
