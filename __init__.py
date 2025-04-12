''' Heat generator for ladders '''

import logging
import RHUtils
import random
import json
from eventmanager import Evt
from HeatGenerator import HeatGenerator, HeatPlan, HeatPlanSlot, SeedMethod
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)



def generateHeats(rhapi, generate_args=None):
    prefix = rhapi.__(generate_args.get('prefix', 'Heat'))
    if generate_args.get('qualifiers_per_heat'):
        pilots_per_heat = int(generate_args['qualifiers_per_heat'])
    else:
        pilots_per_heat = 4

    # Number of heats
    num_heats = len(rhapi.db.heats)
    pilot_results = {}

    # Get all pilots
    pilots = rhapi.db.pilots
    for pilot in pilots:
        pilot_results[pilot.id] = {"points": 0, "consecutives_base": 0, "consecutives": 0.0, "callsign": pilot.callsign}

    # Get all classes ranking
    raceclasses = rhapi.db.raceclasses
    for raceclass in raceclasses:
        ranking = rhapi.db.raceclass_ranking(raceclass.id)
        if ranking:
            for entry in ranking["ranking"]:
                if "points" not in entry:
                    continue
                pilot_results[entry["pilot_id"]]["points"] += entry["points"]

    # Get all pilots consecutives for secondary sorting key
    event_results = rhapi.db.event_results()
    if event_results:
        for entry in event_results["by_consecutives"]:
            pilot_results[entry["pilot_id"]]["consecutives_base"] = entry["consecutives_base"]
            pilot_results[entry["pilot_id"]]["consecutives"] = entry["consecutives_raw"]

    # sort by points
    pilot_results = dict(
            sorted(
                pilot_results.items(), key=lambda item: (
                    -item[1]["points"],
                    -item[1]["consecutives_base"],
                    item[1]["consecutives"],
                    item[1]["callsign"]
                )
            )
        )
    pilots = list(pilot_results.keys())
    heats = [pilots[i:i+pilots_per_heat] for i in range(0, len(pilots), 4)]

    # Some debug info
    for pilot_id, pilot_result in pilot_results.items():
        logging.info(f"Pilot {pilot_id} -> {pilot_result}")

    # generate plan
    plan = []
    for idx, heat in enumerate(heats):
        heat_plan = HeatPlan(name=f"Heat {idx + num_heats + 1}", slots=[])
        for pilot in heat:
            heat_plan.slots.append(HeatPlanSlot(
                method = SeedMethod.PILOT_ID,
                seed_rank = idx,
                pilot_id = pilot
                )
            )
        plan.append(heat_plan)

    return plan

def register_handlers(args):
    generator = HeatGenerator(
            label = "Ranked fill from all classes",
            generator_fn = generateHeats,
            settings = [
                UIField('max_pilots_per_heat', "Maximum pilots per heat", UIFieldType.BASIC_INT, placeholder="Auto"),
                UIField('prefix', "Heat title prefix", UIFieldType.TEXT, placeholder="Main", value="Main"),
            ],
        )
    args['register_fn'](generator)

def initialize(rhapi):
    rhapi.events.on(Evt.HEAT_GENERATOR_INITIALIZE, register_handlers)

