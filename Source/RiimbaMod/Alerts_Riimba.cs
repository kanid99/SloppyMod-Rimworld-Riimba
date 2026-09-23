using System.Collections.Generic;
using System.Linq;
using RimWorld;
using Verse;

namespace RiimbaMod
{
    // The three ways a Riimba quietly stops working. Without these the only way to notice any of
    // them was to click on each unit or station in turn, which nobody does until the floors are
    // already filthy.
    //
    // No "waste output blocked" alert, deliberately: a station never actually blocks. When its
    // output spot is occupied it places waste on the nearest free cell instead, so there is no
    // stuck state to report - only a pile, which is visible without one.
    //
    // RimWorld finds alerts by reflection (every non-abstract Alert subclass), and evaluates one
    // per frame round-robin, so a scan of the player's pawns per evaluation is well inside what
    // vanilla's own alerts do.
    internal static class RiimbaAlertUtility
    {
        public static IEnumerable<Pawn> PlayerUnits()
        {
            List<Map> maps = Find.Maps;
            for (int i = 0; i < maps.Count; i++)
            {
                IReadOnlyList<Pawn> pawns = maps[i].mapPawns.SpawnedPawnsInFaction(Faction.OfPlayer);
                for (int j = 0; j < pawns.Count; j++)
                {
                    if (pawns[j].def == RiimbaDefOf.Riimba && !pawns[j].Dead)
                        yield return pawns[j];
                }
            }
        }

        public static IEnumerable<Building_RiimbaStation> PlayerStations()
        {
            List<Map> maps = Find.Maps;
            for (int i = 0; i < maps.Count; i++)
            {
                List<Building> buildings = maps[i].listerBuildings.allBuildingsColonist;
                for (int j = 0; j < buildings.Count; j++)
                {
                    if (buildings[j] is Building_RiimbaStation station)
                        yield return station;
                }
            }
        }
    }

    public class Alert_RiimbaFlat : Alert
    {
        private readonly List<Pawn> culprits = new List<Pawn>();

        public Alert_RiimbaFlat()
        {
            defaultLabel = "Riimba.AlertFlatLabel".Translate();
            defaultExplanation = "Riimba.AlertFlatDesc".Translate();
        }

        public override AlertReport GetReport()
        {
            culprits.Clear();
            foreach (Pawn unit in RiimbaAlertUtility.PlayerUnits())
            {
                CompRiimbaUnit comp = unit.GetComp<CompRiimbaUnit>();
                if (comp != null && comp.OutOfCharge)
                    culprits.Add(unit);
            }

            return AlertReport.CulpritsAre(culprits);
        }
    }

    public class Alert_RiimbaNoStation : Alert
    {
        private readonly List<Pawn> culprits = new List<Pawn>();

        public Alert_RiimbaNoStation()
        {
            defaultLabel = "Riimba.AlertNoStationLabel".Translate();
            defaultExplanation = "Riimba.AlertNoStationDesc".Translate();
        }

        public override AlertReport GetReport()
        {
            culprits.Clear();
            foreach (Pawn unit in RiimbaAlertUtility.PlayerUnits())
            {
                CompRiimbaUnit comp = unit.GetComp<CompRiimbaUnit>();
                if (comp != null && comp.Station == null)
                    culprits.Add(unit);
            }

            return AlertReport.CulpritsAre(culprits);
        }
    }

    // A station only - not its units - because the station is the thing to fix, and listing
    // three parked units per unpowered station would just be the same problem three times.
    // Stations with nobody signed on are left out: an unpowered spare is not a problem.
    public class Alert_RiimbaStationUnpowered : Alert
    {
        private readonly List<Thing> culprits = new List<Thing>();

        public Alert_RiimbaStationUnpowered()
        {
            defaultLabel = "Riimba.AlertUnpoweredLabel".Translate();
            defaultExplanation = "Riimba.AlertUnpoweredDesc".Translate();
        }

        public override AlertReport GetReport()
        {
            culprits.Clear();
            foreach (Building_RiimbaStation station in RiimbaAlertUtility.PlayerStations())
            {
                if (!station.PowerOn && station.Units.Any(u => u != null && !u.Dead))
                    culprits.Add(station);
            }

            return AlertReport.CulpritsAre(culprits);
        }
    }
}
