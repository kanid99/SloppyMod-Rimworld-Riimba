using System.Collections.Generic;
using UnityEngine;
using Verse;

namespace RiimbaMod
{
    // Picks the allowed area for every selected unit that shares this one's current area.
    //
    // The label names the area, so units on different areas show as separate buttons rather than
    // one button that silently reports only the first unit's setting. Units that do share a
    // button get one menu between them, collected the same way Command_RiimbaRadius collects
    // stations.
    public class Command_RiimbaArea : Command
    {
        public CompRiimbaUnit unit;

        private List<CompRiimbaUnit> units;

        public override void ProcessInput(Event ev)
        {
            base.ProcessInput(ev);

            if (units == null)
                units = new List<CompRiimbaUnit>();

            if (!units.Contains(unit))
                units.Add(unit);

            // Vanilla's own menu: every area that can be assigned as allowed, "Unrestricted",
            // and a shortcut to the area manager - the same list a colonist's schedule offers.
            AreaUtility.MakeAllowedAreaListFloatMenu(area =>
            {
                foreach (CompRiimbaUnit selected in units)
                    selected.AllowedArea = area;
            }, addNullAreaOption: true, addManageOption: true, unit.parent.Map);
        }

        public override bool InheritInteractionsFrom(Gizmo other)
        {
            if (units == null)
                units = new List<CompRiimbaUnit>();

            units.Add(((Command_RiimbaArea)other).unit);

            // One menu for the group, not one per unit - see Command_RiimbaRadius.
            return false;
        }
    }
}
