using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Verse;

namespace RiimbaMod
{
    [StaticConstructorOnStartup]
    public static class RiimbaTextures
    {
        // Drawn by Source/Art/riimba_icons.py rather than borrowed from vanilla: the nearest
        // vanilla command icon by shape is SetTargetFuelLevel, which is a fuel drop, and a
        // button whose picture means something else has to be learned instead of read.
        public static readonly Texture2D SetRadius =
            ContentFinder<Texture2D>.Get("UI/Commands/RiimbaRadius");

        // Vanilla's own allowed-area icon: this command does exactly what that designator's
        // areas are for, so the picture the player already knows is the right one.
        public static readonly Texture2D SetArea =
            ContentFinder<Texture2D>.Get("UI/Designators/AreaAllowedExpand");
    }

    // Sets the broadcast radius of every selected station in one go.
    //
    // Built the way vanilla builds Command_SetTargetFuelLevel, because that is the behaviour
    // players already expect from a gizmo that configures a number: identical commands group in
    // the gizmo bar (Command.GroupsWith compares label, icon and hotkey), the one that gets drawn
    // collects the rest through InheritInteractionsFrom, and the click then applies to all of
    // them. A plain Command_Action would look identical and quietly set one station of six.
    public class Command_RiimbaRadius : Command
    {
        public Building_RiimbaStation station;

        private List<Building_RiimbaStation> stations;

        public override void ProcessInput(Event ev)
        {
            base.ProcessInput(ev);

            if (stations == null)
                stations = new List<Building_RiimbaStation>();

            if (!stations.Contains(station))
                stations.Add(station);

            // The range the slider offers has to be one every selected station can actually
            // take, which is the intersection of their limits rather than this one's. They are
            // usually all the same def and this collapses to that def's numbers; it matters the
            // moment a submod adds a second station with a different reach.
            int from = Mathf.CeilToInt(stations.Max(s => s.MinRadius));
            int to = Mathf.FloorToInt(stations.Min(s => s.MaxRadius));

            if (to < from)
                to = from;

            Find.WindowStack.Add(new Dialog_Slider(
                value => "Riimba.RadiusSlider".Translate(
                    value, station.PowerForRadius(value).ToString("F0")),
                from,
                to,
                value =>
                {
                    foreach (Building_RiimbaStation selected in stations)
                        selected.SetRadius(value);
                },
                Mathf.Clamp(Mathf.RoundToInt(station.Radius), from, to)));
        }

        public override bool InheritInteractionsFrom(Gizmo other)
        {
            if (stations == null)
                stations = new List<Building_RiimbaStation>();

            stations.Add(((Command_RiimbaRadius)other).station);

            // False, so GizmoGridDrawer does not also call ProcessInput on each of the others:
            // this one already holds every selected station and opens a single slider for all
            // of them. True would open one slider per station. Same as vanilla's fuel command.
            return false;
        }
    }
}
