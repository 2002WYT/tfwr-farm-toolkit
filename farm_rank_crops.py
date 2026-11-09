from farm_ops import run
from farm_rank_crop_cactus import rank_cactus
from farm_rank_crop_power import rank_power
from farm_rank_crop_pumpkin import rank_pumpkin


def run_rank_crop(mode, single, target, variant=3):
    if variant < 1 or variant > 5 or target < 1:
        return False
    if mode == "cactus":
        item = Items.Cactus
        water = 0
        route = rank_cactus
    elif mode == "pumpkin":
        item = Items.Pumpkin
        water = 0.1
        route = rank_pumpkin
    elif mode == "power":
        item = Items.Power
        water = 0.1
        route = rank_power
    else:
        return False
    # Variant 1 is the same-seed baseline. Higher variants run the candidate routes.
    if variant > 1:
        return route(single, target, variant)
    workers = 0
    if single:
        workers = 1
    while num_items(item) < target:
        before = num_items(item)
        if not run(mode, 1, workers, water) or num_items(item) <= before:
            return False
    return True
