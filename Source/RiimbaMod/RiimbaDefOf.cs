using RimWorld;
using Verse;

namespace RiimbaMod
{
    [DefOf]
    public static class RiimbaDefOf
    {
        public static JobDef Riimba_Clean;
        public static JobDef Riimba_Dock;
        public static JobDef Riimba_SignOn;

        public static ThingDef Riimba;
        public static ThingDef RiimbaStation;
        public static ThingDef RiimbaWasteHopper;

        public static StatDef RiimbaChargeSpeed;
        public static StatDef RiimbaRadiusBonus;

        static RiimbaDefOf()
        {
            DefOfHelper.EnsureInitializedInCtor(typeof(RiimbaDefOf));
        }
    }

    // Reach and team size, read off the station's def. See Buildings_RiimbaStation.xml for why
    // this is an extension rather than a comp.
    public class RiimbaStationExtension : DefModExtension
    {
        // Where a newly built station's radius starts, and the range its slider allows. The
        // radius itself lives on the building, not here - it is per-station state the player
        // sets and the save has to keep.
        public float radius = 15f;
        public float minRadius = 6f;
        public float maxRadius = 30f;

        // Watts per tile of floor inside the ring, over and above what the smallest setting
        // already covers.
        //
        // Per tile of AREA, deliberately, which makes the cost grow with the square of the
        // radius. Charging per tile of radius instead would be the same money for four times
        // the floor every time the ring doubled, and there would be no decision left to make:
        // every station would sit at maximum. This way the last few tiles of reach are the
        // expensive ones, so a small station covering a workshop is cheap and a station meant
        // to cover half a base costs real generating capacity.
        public float powerPerCoveredTile = 0.2f;

        public int maxUnits = 3;
        public float powerPerChargingUnit = 150f;
    }
}
