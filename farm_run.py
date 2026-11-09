from farm_daily import run_farm

# Use farm_get_* for a fixed resource or edit these settings.
# Valid MODE values
# hay, wood, carrot, pumpkin, power (sunflowers)
# cactus, bone (dinosaurs), gold (mazes), substance (Weird Substance)
# water, fertilizer
MODE = "hay"
# Gold collects one chest per maze per round.
# Water and fertilizer wait 10 game seconds per round.
ROUNDS = 1

# WORKERS = 0 uses all drones. The dinosaur route uses one drone.
WORKERS = 0
# WATER_BELOW = 0 disables watering. 0.1 waters below 10% moisture.
WATER_BELOW = 0
# MIXED = True enables companion planting for hay, wood, and carrots.
MIXED = True

clear()
run_farm(MODE, ROUNDS, WORKERS, WATER_BELOW, MIXED)
