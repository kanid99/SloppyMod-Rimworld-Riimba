using System;
using UnityEngine;

namespace RiimbaMod
{
    // The seam between this assembly and the optional trash chute.
    //
    // The chute is built on Vanilla Expanded Framework's pipe system, which this assembly must
    // not reference: a hard reference would make the whole mod fail to load for anyone without
    // it. So the chute lives in a second assembly under Mods/TrashChute, which RimWorld only
    // loads when Vanilla Recycling Expanded (and with it the framework) is active - see
    // LoadFolders.xml - and that assembly plugs itself in here at startup. With it absent the
    // handler stays null, ChuteAvailable is false, and every station puts trash on its spot.
    public static class RiimbaWasteRouting
    {
        // Takes a station and a count of whole trash items; returns how many the chute took.
        public static Func<Building_RiimbaStation, int, int> chuteHandler;

        public static bool ChuteAvailable => chuteHandler != null;

        public static bool ChuteSelected =>
            ChuteAvailable && RiimbaModMain.Settings.wasteOutput == RiimbaWasteOutput.Chute;

        // Whatever the chute does not take stays with the caller, which puts it on the spot.
        // Never the other way round: trash that neither went down the chute nor onto the floor
        // would be trash deleted, and a full or disconnected chute should be visible as a pile
        // on the output spot, not as waste quietly vanishing.
        public static int TryPushTrash(Building_RiimbaStation station, int count)
        {
            if (count <= 0 || station == null || !ChuteSelected)
                return 0;

            return Mathf.Clamp(chuteHandler(station, count), 0, count);
        }
    }
}
