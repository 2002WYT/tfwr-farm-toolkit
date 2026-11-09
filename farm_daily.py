from farm_ops import run
from farm_daily_crops import run_power_daily, run_pumpkin_daily
from farm_daily_fast import run_bones_daily, run_cactus_daily
from farm_daily_fast import run_gold_preferred
from farm_daily_mixfast import run_daily_mixfast
from farm_daily_poly import run_wood_daily


def run_farm(mode, rounds, workers=0, water_below=0, mixed=True):
    if mode == "cactus":
        run_cactus_daily(rounds, workers, water_below, 4)
    elif mode == "gold":
        run_gold_preferred(rounds, workers)
    elif mode == "bone":
        run_bones_daily(rounds, True)
    elif mode == "pumpkin":
        run_pumpkin_daily(rounds, workers, water_below)
    elif mode == "power":
        run_power_daily(rounds, workers, water_below)
    elif mixed and mode == "wood":
        run_wood_daily(rounds, workers, water_below)
    elif mixed and (mode == "hay" or mode == "carrot"):
        run_daily_mixfast(mode, rounds, workers, water_below)
    else:
        run(mode, rounds, workers, water_below)
