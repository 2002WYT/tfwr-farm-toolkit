from farm_rank_bone import run_rank_bone
from farm_rank_core import compete, rank_profile
from farm_rank_crops import run_rank_crop
from farm_rank_hay_reference import run_multi_hay, run_single_hay
from farm_rank_maze import run_rank_maze
from farm_rank_poly import run_rank_poly
from farm_rank_poly_carrot import run_rank_poly_carrot
from farm_rank_poly_fast import run_rank_poly_fast


def candidate(mode, single, variant):
    if variant == 0:
        return compete(mode, single)
    leaderboard, item, target, water = rank_profile(mode, single)
    if mode == "hay" or mode == "wood" or mode == "carrot":
        if mode == "hay" and variant == 8:
            if single:
                run_single_hay()
            else:
                run_multi_hay()
            return num_items(item) >= target
        if mode == "carrot" and not single and variant >= 6:
            return run_rank_poly_carrot(target, variant - 5)
        if variant >= 4:
            return run_rank_poly_fast(mode, single, target, variant - 3)
        return run_rank_poly(mode, single, target, variant)
    if mode == "cactus" or mode == "pumpkin" or mode == "power":
        return run_rank_crop(mode, single, target, variant)
    if mode == "gold":
        return run_rank_maze(single, target, variant)
    if mode == "bone":
        return run_rank_bone(target, variant)
    return False
