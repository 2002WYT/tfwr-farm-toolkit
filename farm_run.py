from farm_ops import run
from farm_daily_crops import run_power_daily, run_pumpkin_daily
from farm_daily_fast import run_bones_daily, run_cactus_daily, run_gold_preferred
from farm_daily_mixfast import run_daily_mixfast
from farm_daily_poly import run_wood_daily

# Daily settings. Edit these values and press Run in this window. Start with ROUNDS = 1.
# Valid MODE values
# hay, wood, carrot, pumpkin, power (sunflowers)
# cactus, bone (dinosaurs), gold (mazes), substance (Weird Substance)
# water, fertilizer
MODE = "hay"
# ROUNDS is the harvest count. Gold collects one chest per maze per round. Water and fertilizer wait 10 game seconds per round.
ROUNDS = 1

# WORKERS = 0 uses all drones and 1 uses one drone. The dinosaur route always uses one drone.
WORKERS = 0
# WATER_BELOW = 0 disables watering. Set 0.1 to water when moisture falls below 10%.
WATER_BELOW = 0
# MIXED = True enables companion planting for hay, wood, and carrots.
MIXED = True

# The entry point selects a route from the settings above.
if MODE == "cactus":
    run_cactus_daily(ROUNDS, WORKERS, WATER_BELOW, 4)
elif MODE == "gold":
    run_gold_preferred(ROUNDS, WORKERS)
elif MODE == "bone":
    run_bones_daily(ROUNDS, True)
elif MODE == "pumpkin":
    run_pumpkin_daily(ROUNDS, WORKERS, WATER_BELOW)
elif MODE == "power":
    run_power_daily(ROUNDS, WORKERS, WATER_BELOW)
elif MIXED and MODE == "wood":
    run_wood_daily(ROUNDS, WORKERS, WATER_BELOW)
elif MIXED and (MODE == "hay" or MODE == "carrot"):
    run_daily_mixfast(MODE, ROUNDS, WORKERS, WATER_BELOW)
else:
    run(MODE, ROUNDS, WORKERS, WATER_BELOW)
