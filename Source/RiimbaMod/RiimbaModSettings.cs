using UnityEngine;
using Verse;

namespace RiimbaMod
{
    // Where a station puts the trash its units bring back. Wastepacks always go to the output
    // spot whichever this is: the chute carries trash, and a wastepack is not trash - it is the
    // sealed bio-waste that Vanilla Recycling Expanded processes somewhere else entirely.
    public enum RiimbaWasteOutput
    {
        // The station's output spot, or a waste hopper linked to it. Haulers and conveyor mods
        // pick up from there.
        Spot,

        // The trash chute pipe network. Only available with Vanilla Recycling Expanded loaded,
        // which brings the pipe framework and the compactor the chute feeds; without it this
        // behaves as Spot.
        Chute,
    }

    public class RiimbaModSettings : ModSettings
    {
        // Off means units clean without producing anything. The station's waste readout and dump
        // command disappear with it, rather than sitting at zero forever.
        public bool generateWaste = true;

        // Scales how much waste a given amount of filth packs down into.
        public float wasteMultiplier = 1.0f;

        // Scales charge drain only, not the gain. Set to 0 for units that never need to dock,
        // which is the "I just want a cleaning robot" setting.
        public float chargeDrainMultiplier = 1.0f;

        // Off means a unit works anywhere on the map its station can see, ignoring the radius.
        // The station still commands it and still takes its waste.
        public bool enforceRadius = true;

        // On means a unit goes to messes in a hospital first and a kitchen second before the
        // nearest one anywhere else. Those are the two rooms where dirt does harm rather than
        // just looking bad - infection after surgery, food poisoning from the stove.
        public bool prioritizeRooms = true;

        public RiimbaWasteOutput wasteOutput = RiimbaWasteOutput.Spot;

        // Field-by-field rather than replacing the settings object, because Mod.GetSettings hands
        // out a single instance that everything else already holds a reference to.
        public void ResetToDefaults()
        {
            RiimbaModSettings defaults = new RiimbaModSettings();

            generateWaste = defaults.generateWaste;
            wasteMultiplier = defaults.wasteMultiplier;
            chargeDrainMultiplier = defaults.chargeDrainMultiplier;
            enforceRadius = defaults.enforceRadius;
            prioritizeRooms = defaults.prioritizeRooms;
            wasteOutput = defaults.wasteOutput;
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Values.Look(ref generateWaste, "generateWaste", true);
            Scribe_Values.Look(ref wasteMultiplier, "wasteMultiplier", 1.0f);
            Scribe_Values.Look(ref chargeDrainMultiplier, "chargeDrainMultiplier", 1.0f);
            Scribe_Values.Look(ref enforceRadius, "enforceRadius", true);
            Scribe_Values.Look(ref prioritizeRooms, "prioritizeRooms", true);
            Scribe_Values.Look(ref wasteOutput, "wasteOutput", RiimbaWasteOutput.Spot);
        }
    }

    public class RiimbaModMain : Mod
    {
        private static void WasteOutputSelector(Listing_Standard listing)
        {
            listing.Label("    Trash goes to:");

            if (listing.RadioButton("The output spot",
                    Settings.wasteOutput == RiimbaWasteOutput.Spot, tabIn: 24f,
                    tooltip: "Put out on the station's output spot, or into a waste hopper linked "
                        + "to it. Haulers collect it from there, and so will a conveyor belt "
                        + "pointed at a hopper."))
                Settings.wasteOutput = RiimbaWasteOutput.Spot;

            // Offered only when the chute can actually exist. Selecting it without the pipe
            // framework loaded would be a setting that silently does nothing.
            if (RiimbaWasteRouting.ChuteAvailable)
            {
                if (listing.RadioButton("The trash chute",
                        Settings.wasteOutput == RiimbaWasteOutput.Chute, tabIn: 24f,
                        tooltip: "Piped away through trash chutes connected to the station, into "
                            + "a garbage compactor or a chute outlet. A station that is not "
                            + "connected, or whose chute is full, falls back to its output spot "
                            + "rather than holding the trash. Wastepacks always use the spot."))
                    Settings.wasteOutput = RiimbaWasteOutput.Chute;
            }
            else
            {
                listing.Label("        The trash chute needs Vanilla Recycling Expanded.");
            }
        }

        public static RiimbaModSettings Settings;

        public RiimbaModMain(ModContentPack content) : base(content)
        {
            Settings = GetSettings<RiimbaModSettings>();
        }

        public override void DoSettingsWindowContents(Rect inRect)
        {
            Listing_Standard listing = new Listing_Standard();
            listing.Begin(inRect);

            Header(listing, "Waste");

            listing.CheckboxLabeled(
                "Cleaning produces waste",
                ref Settings.generateWaste,
                "When enabled, everything a unit lifts off the floor is packed into its bin and "
                + "handed to its station, which puts it out as trash or wastepacks. Turn this off "
                + "and units simply clean, producing nothing.");

            if (Settings.generateWaste)
            {
                listing.Label($"    Waste per mess cleaned: {Settings.wasteMultiplier:F2}x");
                Settings.wasteMultiplier = listing.Slider(Settings.wasteMultiplier, 0f, 3f);
                listing.Label("    Scales both trash and wastepacks. Bin capacity is unchanged, so "
                            + "a higher setting also means more trips back to the station.");

                listing.Gap(6f);
                WasteOutputSelector(listing);
            }

            listing.Gap();
            Header(listing, "Charge");

            listing.Label($"Charge drain: {Settings.chargeDrainMultiplier:F2}x");
            Settings.chargeDrainMultiplier = listing.Slider(Settings.chargeDrainMultiplier, 0f, 3f);
            listing.Label("At zero a unit never runs down and never needs a bay to charge at. It "
                        + "still docks to unload its bin.");

            listing.Gap();
            Header(listing, "Range");

            listing.CheckboxLabeled(
                "Units stay inside their station's radius",
                ref Settings.enforceRadius,
                "When enabled, a unit only cleans within its station's broadcast radius - the "
                + "ring drawn around the station, set per station with the command on it, and "
                + "paid for in power. Turn this off and a unit works anywhere it can reach on "
                + "the map, while still docking at its station; the radius then costs nothing "
                + "to hold, because it is no longer holding anything in.");

            listing.Gap();
            Header(listing, "Work");

            listing.CheckboxLabeled(
                "Clean hospitals and kitchens first",
                ref Settings.prioritizeRooms,
                "When enabled, a unit clears every mess it can reach in a hospital before anything "
                + "else, then every mess in a kitchen, and only then goes to whatever is nearest. "
                + "Those are the rooms where dirt raises the chance of infection and of food "
                + "poisoning. Turn this off and units simply clean whatever is closest.");

            listing.Gap();
            if (listing.ButtonText("Reset to defaults"))
            {
                Settings.ResetToDefaults();
            }

            listing.End();
            base.DoSettingsWindowContents(inRect);
        }

        private static void Header(Listing_Standard listing, string label)
        {
            Text.Font = GameFont.Small;
            GUI.color = new Color(0.72f, 0.82f, 0.86f);
            listing.Label(label);
            GUI.color = Color.white;
            listing.GapLine(2f);
        }

        public override string SettingsCategory()
        {
            return "SloppyMods Riimba";
        }
    }
}
