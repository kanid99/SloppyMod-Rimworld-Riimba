using System.Collections.Generic;
using UnityEngine;
using Verse;

namespace RiimbaMod
{
    // Spot geometry, kept free of any Thing instance so the place worker can draw the same spots
    // from a hypothetical footprint while the building is still a ghost on the cursor. The
    // building and the ghost therefore cannot disagree about where the bays are.
    public static class RiimbaSpots
    {
        // The row of cells just outside one end of the footprint. `front` is the side the
        // building FACES, matching the mending mod's convention so the two read the same way.
        public static List<IntVec3> EdgeCells(CellRect rect, Rot4 rot, bool front)
        {
            IntVec3 dir = front ? rot.FacingCell : rot.Opposite.FacingCell;
            List<IntVec3> cells = new List<IntVec3>();

            if (dir.x != 0)
            {
                int x = dir.x > 0 ? rect.maxX + 1 : rect.minX - 1;
                for (int z = rect.minZ; z <= rect.maxZ; z++)
                    cells.Add(new IntVec3(x, 0, z));
            }
            else
            {
                int z = dir.z > 0 ? rect.maxZ + 1 : rect.minZ - 1;
                for (int x = rect.minX; x <= rect.maxX; x++)
                    cells.Add(new IntVec3(x, 0, z));
            }

            return cells;
        }

        // One bay per cell along the front row - INSIDE the footprint, not outside it.
        //
        // The station is three wide and two deep for exactly this reason. The back row is the
        // machine; the front row is three open bays, and a unit drives onto one of the
        // building's own cells to dock. That is what lets the station's overhang mask the
        // unit's back end as it reverses in: the lip is then drawn over cells that belong to
        // the building, rather than over the open floor in front of it.
        //
        // Deliberately one bay per unit rather than a single shared docking cell: three units
        // queueing for one tile is three units standing in each other's way, and a unit that
        // cannot reach the dock cannot charge.
        public static List<IntVec3> BayCells(CellRect rect, Rot4 rot)
        {
            return FrontRowCells(rect, rot);
        }

        // The row of the footprint nearest the side the building faces.
        public static List<IntVec3> FrontRowCells(CellRect rect, Rot4 rot)
        {
            IntVec3 dir = rot.FacingCell;
            List<IntVec3> cells = new List<IntVec3>();

            if (dir.x != 0)
            {
                int x = dir.x > 0 ? rect.maxX : rect.minX;
                for (int z = rect.minZ; z <= rect.maxZ; z++)
                    cells.Add(new IntVec3(x, 0, z));
            }
            else
            {
                int z = dir.z > 0 ? rect.maxZ : rect.minZ;
                for (int x = rect.minX; x <= rect.maxX; x++)
                    cells.Add(new IntVec3(x, 0, z));
            }

            return cells;
        }

        // Where a unit lines up before reversing in: the cell directly in front of its bay,
        // just outside the building. It drives here nose-first, turns on the spot, then backs
        // onto the bay - see JobDriver_RiimbaDock.
        public static IntVec3 ApproachCellFor(IntVec3 bay, Rot4 rot)
        {
            return bay + rot.FacingCell;
        }

        // Waste goes out the back, away from the bays, so a unit arriving to dock never has to
        // path through the pile the station just put down.
        public static IntVec3 WasteOutputCell(CellRect rect, Rot4 rot)
        {
            List<IntVec3> back = EdgeCells(rect, rot, front: false);
            return back[back.Count / 2];
        }

        public static void DrawSpots(CellRect rect, Rot4 rot, float radius)
        {
            foreach (IntVec3 cell in BayCells(rect, rot))
                DrawRing(cell, SimpleColor.Cyan);

            DrawRing(WasteOutputCell(rect, rot), SimpleColor.Orange);

            Map map = Find.CurrentMap;
            if (map != null && radius > 0f)
            {
                // The command radius is measured from the centre of the footprint, which is what
                // Building_RiimbaStation.InRadius tests against.
                GenDraw.DrawRadiusRing(rect.CenterCell, radius);
            }
        }

        private static void DrawRing(IntVec3 cell, SimpleColor colour)
        {
            Map map = Find.CurrentMap;
            if (map == null || !cell.InBounds(map))
                return;

            GenDraw.DrawCircleOutline(cell.ToVector3Shifted(), 0.44f, colour);
        }
    }

    // Draws the bays and the command radius while the building is still on the cursor, so its
    // orientation and reach can be judged before it is committed.
    public class PlaceWorker_RiimbaStation : PlaceWorker
    {
        public override void DrawGhost(ThingDef def, IntVec3 center, Rot4 rot, Color ghostCol, Thing thing = null)
        {
            base.DrawGhost(def, center, rot, ghostCol, thing);

            RiimbaStationExtension ext = def.GetModExtension<RiimbaStationExtension>();
            RiimbaSpots.DrawSpots(GenAdj.OccupiedRect(center, rot, def.Size), rot, ext?.radius ?? 0f);
        }
    }
}
