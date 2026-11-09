from farm_ops import run
from farm_mix import run_mix
from farm_gold import gold_geometry


# Leaderboard settings. Set CATEGORY and SINGLE_DRONE, then run farm_rank.
# Valid CATEGORY values include hay, wood, carrot, pumpkin, power, cactus, gold, and bone.
# Use power for sunflowers, gold for mazes, and bone for dinosaurs.
CATEGORY = "cactus"
# SINGLE_DRONE = True selects the single-drone board. Set it to False for dinosaurs.
SINGLE_DRONE = False
# MIXED affects only the variant 0 baseline for hay, wood, and carrots.
MIXED = True
# VARIANT = -1 selects the verified route. Use 0 for the baseline or a positive number to retest a variant.
VARIANT = -1


def preferred_variant(mode, single):
    if VARIANT >= 0:
        return VARIANT
    # Each pair lists the multi-drone variant first. Daily harvesting checks its own prerequisites.
    variants = {
        "hay": (8, 8), "wood": (4, 2), "carrot": (6, 2), "pumpkin": (5, 5),
        "power": (3, 3), "cactus": (4, 2), "gold": (3, 3), "bone": (8, 8),
    }
    index = 0
    if single:
        index = 1
    return variants[mode][index]


def rank_profile(mode, single):
    if single:
        return {
            "hay": (Leaderboards.Hay_Single, Items.Hay, 100000000, 0),
            "wood": (Leaderboards.Wood_Single, Items.Wood, 500000000, 0.1),
            "carrot": (Leaderboards.Carrots_Single, Items.Carrot, 100000000, 0.1),
            "pumpkin": (Leaderboards.Pumpkins_Single, Items.Pumpkin, 10000000, 0.1),
            "power": (Leaderboards.Sunflowers_Single, Items.Power, 10000, 0.1),
            "cactus": (Leaderboards.Cactus_Single, Items.Cactus, 131072, 0),
            "gold": (Leaderboards.Maze_Single, Items.Gold, 616448, 0),
        }[mode]
    return {
        "hay": (Leaderboards.Hay, Items.Hay, 2000000000, 0),
        "wood": (Leaderboards.Wood, Items.Wood, 10000000000, 0.1),
        "carrot": (Leaderboards.Carrots, Items.Carrot, 2000000000, 0.1),
        "pumpkin": (Leaderboards.Pumpkins, Items.Pumpkin, 200000000, 0.1),
        "power": (Leaderboards.Sunflowers, Items.Power, 100000, 0.1),
        "cactus": (Leaderboards.Cactus, Items.Cactus, 33554432, 0),
        "gold": (Leaderboards.Maze, Items.Gold, 9863168, 0),
        "bone": (Leaderboards.Dinosaur, Items.Bone, 33488928, 0),
    }[mode]


def compete(mode, single):
    leaderboard, item, target, water = rank_profile(mode, single)
    workers = 0
    if single:
        workers = 1
    start = get_time()
    quick_print("[RANK START]", leaderboard, "target", target, "size", get_world_size(), "workers", workers)
    if MIXED and (mode == "hay" or mode == "wood" or mode == "carrot"):
        # Reuse the blocks and companions across the entire run. Clean up after reaching the target.
        ok = run_mix(mode, 1, workers, water, target)
        if not ok or num_items(item) < target:
            quick_print("[RANK FAIL]", leaderboard, "current", num_items(item), "target", target)
            return False
        quick_print("[RANK PASS]", leaderboard, "current", num_items(item), "target", target,
                    "seconds", get_time() - start)
        return True

    rounds = 1
    if mode == "gold":
        # Reuse the full-field maze with one drone, or run separate mazes in parallel.
        active, grid, stride, side = gold_geometry(get_world_size(), workers)
        scale = 2 ** (num_unlocked(Unlocks.Mazes) - 1)
        per_round = active * side ** 2 * scale
        rounds = max(1, (target - num_items(item) + per_round - 1) // per_round)
    while num_items(item) < target:
        before = num_items(item)
        ok = run(mode, rounds, workers, water)
        after = num_items(item)
        if not ok or after <= before:
            quick_print("[RANK FAIL]", leaderboard, "current", after, "target", target)
            return False
    quick_print("[RANK PASS]", leaderboard, "current", num_items(item), "target", target,
                "seconds", get_time() - start)
    return True
