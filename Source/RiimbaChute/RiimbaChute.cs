using System;
using System.Collections.Generic;
using System.Reflection;
using PipeSystem;
using RimWorld;
using RiimbaMod;
using UnityEngine;
using Verse;

namespace RiimbaChute
{
    // The trash chute: Vanilla Expanded Framework's pipe system carrying trash from Riimba control
    // stations to wherever it is wanted.
    //
    // The pieces, and which side of the framework each sits on:
    //
    //   station     a CompResourceStorage patched onto RiimbaStation - a small tank the station
    //               fills with trash through RiimbaWasteRouting instead of dropping it
    //   chute       the pipe, pure framework
    //   compactor   CompRiimbaChuteIntake, patched onto Vanilla Recycling Expanded's garbage
    //               compactor, which draws trash out of the network and loads it into the
    //               compactor exactly as a hauler would
    //   outlet      a framework CompConvertToThing that turns chute trash back into items on its
    //               own cell, for a stockpile, a hauler or a conveyor
    //
    // The framework moves stored resource to converters on its own tick, so the outlet needs no
    // code; the intake does, because the compactor is not a Building_Storage and the framework
    // has no way to put items into a container.
    [StaticConstructorOnStartup]
    public static class RiimbaChuteBootstrap
    {
        static RiimbaChuteBootstrap()
        {
            RiimbaWasteRouting.chuteHandler = PushTrash;
        }

        // Takes only what the station's tank has room for, and only when the chute actually
        // leads somewhere. A station sitting on a length of pipe that goes nowhere would otherwise
        // fill its tank and hold that trash indefinitely; instead it refuses, and the trash goes
        // on the output spot where the player can see something is wrong.
        private static int PushTrash(Building_RiimbaStation station, int count)
        {
            if (station == null || !station.Spawned)
                return 0;

            CompResourceStorage tank = station.GetComp<CompResourceStorage>();
            if (tank?.PipeNet == null || !LeadsSomewhere(tank.PipeNet))
                return 0;

            int taken = Mathf.Min(count, Mathf.FloorToInt(tank.AmountCanAccept));
            if (taken <= 0)
                return 0;

            tank.AddResource(taken);
            return taken;
        }

        private static bool LeadsSomewhere(PipeNet net)
        {
            if (net.thingConverters.Count > 0)
                return true;

            List<CompResource> connectors = net.connectors;
            for (int i = 0; i < connectors.Count; i++)
            {
                if (connectors[i] is CompRiimbaChuteIntake)
                    return true;
            }

            return false;
        }
    }

    public class CompProperties_RiimbaChuteIntake : CompProperties_Resource
    {
        // The item the network's resource becomes when it is loaded - one unit, one item.
        public ThingDef thing;

        // How often the intake pulls. The compactor takes a long time over each item, so there is
        // nothing to gain from checking every tick.
        public int ticksBetweenPulls = 250;

        public CompProperties_RiimbaChuteIntake()
        {
            compClass = typeof(CompRiimbaChuteIntake);
        }

        public override IEnumerable<string> ConfigErrors(ThingDef parentDef)
        {
            foreach (string error in base.ConfigErrors(parentDef))
                yield return error;

            if (thing == null)
                yield return "CompProperties_RiimbaChuteIntake needs a thing to load.";
        }
    }

    // Loads chute trash into the building's container - VRE's compactor processor, which is a
    // vanilla CompThingContainer underneath. Written against CompThingContainer rather than VRE's
    // own class so this assembly needs no reference to VRE's: if VRE changes its processor, this
    // still compiles and still works for as long as the processor is a thing container.
    public class CompRiimbaChuteIntake : CompResource
    {
        private static readonly Dictionary<Type, PropertyInfo> autoLoadProperties =
            new Dictionary<Type, PropertyInfo>();

        public new CompProperties_RiimbaChuteIntake Props => (CompProperties_RiimbaChuteIntake)props;

        public override void CompTick()
        {
            base.CompTick();

            // A hash interval is safe here: CompTick runs every tick on a Normal ticker, unlike
            // CompTickInterval, whose own throttling can leave a nested hash interval unmet.
            if (parent.IsHashIntervalTick(Props.ticksBetweenPulls))
                Pull();
        }

        private void Pull()
        {
            if (PipeNet == null || Props.thing == null || !parent.Spawned)
                return;

            CompThingContainer container = parent.GetComp<CompThingContainer>();
            if (container == null || !AutoLoadOn(container) || !container.Accepts(Props.thing))
                return;

            int space = container.Props.stackLimit - container.TotalStackCount;
            int available = Mathf.FloorToInt(PipeNet.CurrentStored());
            int count = Mathf.Min(space, available, Props.thing.stackLimit);
            if (count <= 0)
                return;

            Thing trash = ThingMaker.MakeThing(Props.thing);
            trash.stackCount = count;

            // Draw only once the container has actually taken it. The other order would lose the
            // resource from the network whenever the add failed.
            if (!container.innerContainer.TryAdd(trash))
            {
                trash.Destroy();
                return;
            }

            PipeNet.DrawAmongStorage(count, PipeNet.storages);
        }

        // VRE's processor has an auto-load toggle that tells haulers to stop filling it. The
        // chute honours it too - a player who switched it off meant "stop putting trash in", and
        // would not expect a pipe to ignore that. Read by reflection so this assembly needs no
        // reference to VRE's; a container without the toggle counts as always on.
        private static bool AutoLoadOn(CompThingContainer container)
        {
            Type type = container.GetType();
            if (!autoLoadProperties.TryGetValue(type, out PropertyInfo property))
            {
                property = type.GetProperty("AutoLoad", BindingFlags.Public | BindingFlags.Instance);
                if (property != null && property.PropertyType != typeof(bool))
                    property = null;

                autoLoadProperties[type] = property;
            }

            return property == null || (bool)property.GetValue(container);
        }
    }
}
