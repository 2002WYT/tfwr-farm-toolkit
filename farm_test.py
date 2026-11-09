# 在游戏里执行。mix 比较原版和混种；mix-rank 从零跑混种与迷宫的榜单目标。
# validation / extras / rank / rank-full / bones / bone-bench / all / smoke / suite / bench 为已有套件。
from farm_rank_core import rank_profile

SUITE = "mix-rank"
BENCH_MODES = ["hay", "wood", "carrot", "pumpkin", "power", "cactus"]
BENCH_SEEDS = [1709]
SPEEDUP = 64
BONE_SPEEDUP = 1024
PROFILE = {}
for technology in Unlocks:
    level = num_unlocked(technology)
    if level > 0:
        PROFILE[technology] = level

quick_print("[PROFILE]", "farm_size", get_world_size(), "max_drones", max_drones(),
            "pumpkins", num_unlocked(Unlocks.Pumpkins), "cactus", num_unlocked(Unlocks.Cactus),
            "speed", num_unlocked(Unlocks.Speed), "watering", num_unlocked(Unlocks.Watering))


def trial(label, mode, size, workers, seed, setup, rounds, water_below):
    items = {
        Items.Hay: 10000000,
        Items.Wood: 10000000,
        Items.Carrot: 10000000,
        Items.Pumpkin: 10000000,
        Items.Cactus: 0,
        Items.Power: 0,
        Items.Water: 10000,
        Items.Fertilizer: 10000,
        Items.Weird_Substance: 10000000,
    }
    if setup == "shortage":
        cost = get_cost(Entities.Pumpkin)
        for item in cost:
            items[item] = cost[item] * (size * size - 1)
    if mode == "bone":
        items[Items.Cactus] = 1000000
        if setup == "full-baseline" or setup == "full-powered":
            items[Items.Power] = num_items(Items.Power)
        if setup == "no-apple" or setup == "five-apples":
            apples = 0
            if setup == "five-apples":
                apples = 5
            cost = get_cost(Entities.Apple)
            for item in cost:
                items[item] = cost[item] * apples
    if setup == "gold-poor":
        items[Items.Weird_Substance] = 0
    if mode == "water" or mode == "fertilizer":
        items[Items.Water] = 0
        items[Items.Fertilizer] = 0
    if setup == "mix-base" or setup == "mix" or setup == "mix-existing" or setup == "mix-budget":
        items[Items.Power] = 1000000000
        if setup == "mix-budget":
            items[Items.Wood] = 0
            items[Items.Hay] = 0

    profile = PROFILE
    if setup == "rank" or setup == "rank-full":
        profile = Unlocks
        leaderboard, item, target, water = rank_profile(mode, size == 8)
        items[Items.Hay] = 10000000000
        items[Items.Wood] = 10000000000
        items[Items.Carrot] = 10000000000
        items[Items.Pumpkin] = 10000000000
        items[Items.Cactus] = 1000000000
        items[Items.Power] = 1000000000
        items[item] = target - 1
        if mode == "cactus" or setup == "rank-full":
            items[item] = 0
    settings = {
        "label": label,
        "mode": mode,
        "size": size,
        "workers": workers,
        "seed": seed,
        "setup": setup,
        "rounds": rounds,
        "water_below": water_below,
    }
    quick_print("[CASE]", label, "mode", mode, "size", size, "workers", workers, "seed", seed)
    speedup = SPEEDUP
    if mode == "bone":
        speedup = BONE_SPEEDUP
    elif setup == "rank-full":
        speedup = 256
    elapsed = simulate("farm_trial", profile, items, settings, seed, speedup)
    quick_print("[SIM]", label, "seconds", elapsed)
    return elapsed


def compare(mode, size, seed):
    single = trial("single", mode, size, 1, seed, "fresh", 1, 0)
    parallel = trial("parallel", mode, size, 0, seed, "fresh", 1, 0)
    if parallel > 0:
        quick_print("[AB]", mode, "size", size, "seed", seed, "sim_speedup", single / parallel)


def small_suite():
    for mode in ["hay", "wood", "carrot", "pumpkin", "power", "cactus"]:
        for seed in [1709, 8243]:
            compare(mode, 6, seed)
    trial("shortage", "pumpkin", 6, 0, 1709, "shortage", 1, 0)
    trial("occupied", "pumpkin", 6, 0, 1709, "occupied", 1, 0)
    trial("resume", "carrot", 6, 3, 8243, "resume", 2, 0.5)
    trial("odd-stripes", "carrot", 7, 3, 1709, "fresh", 1, 0)
    trial("hay-from-soil", "hay", 6, 0, 8243, "bare-soil", 2, 0)


def benchmark():
    for mode in BENCH_MODES:
        for seed in BENCH_SEEDS:
            compare(mode, 32, seed)


def tune():
    for mode in ["wood", "carrot", "pumpkin", "power"]:
        trial("tune-16", mode, 32, 16, 1709, "fresh", 1, 0)
        trial("tune-24", mode, 32, 24, 1709, "fresh", 1, 0)
        trial("tune-water", mode, 32, 0, 1709, "fresh", 1, 0.1)


def bones_suite():
    trial("bone-small", "bone", 6, 1, 1709, "fresh", 1, 0)
    trial("bone-repeat", "bone", 6, 1, 8243, "fresh", 2, 0)
    trial("bone-no-apple", "bone", 6, 1, 1709, "no-apple", 1, 0)
    trial("bone-five-apples", "bone", 6, 1, 8243, "five-apples", 1, 0)
    trial("bone-occupied", "bone", 6, 1, 8243, "occupied", 1, 0)
    trial("bone-odd", "bone", 7, 1, 1709, "fresh", 1, 0)
    for seed in [1709, 8243]:
        trial("bone-full", "bone", 32, 1, seed, "fresh", 1, 0)


def smoke():
    trial("smoke-single", "hay", 6, 1, 1709, "fresh", 1, 0)
    trial("smoke-parallel", "carrot", 6, 0, 1709, "fresh", 1, 0)


def extras_suite():
    trial("water-30s", "water", 6, 1, 1709, "fresh", 3, 0)
    trial("fertilizer-30s", "fertilizer", 6, 1, 1709, "fresh", 3, 0)
    trial("gold-shortage", "gold", 6, 1, 1709, "gold-poor", 1, 0)
    trial("gold-small", "gold", 6, 1, 1709, "fresh", 3, 0)
    for workers in [1, 4, 0]:
        trial("gold-32", "gold", 32, workers, 1709, "fresh", 8, 0)
    for workers in [1, 0]:
        trial("substance-fertilizer", "substance", 32, workers, 1709, "fresh", 1, 0.1)
        trial("substance-cross", "substance", 32, workers, 1709, "cross", 1, 0.1)


def rank_suite():
    for size in [8, 32]:
        for mode in ["hay", "wood", "carrot", "pumpkin", "power", "cactus", "gold"]:
            trial("rank-target", mode, size, 0, 1709, "rank", 1, 0)


def full_rank_suite():
    for size in [8, 32]:
        for mode in ["gold", "power"]:
            trial("rank-full", mode, size, 0, 1709, "rank-full", 1, 0)


def bone_bench():
    baseline = trial("bone-fixed-powered", "bone", 32, 1, 1709, "full-baseline", 1, 0)
    fast = trial("bone-fast-powered", "bone", 32, 1, 1709, "full-powered", 1, 0)
    if fast > 0:
        quick_print("[AB]", "bone", "size", 32, "seed", 1709, "sim_speedup", baseline / fast)
    trial("bone-fast-powered", "bone", 32, 1, 8243, "full-powered", 1, 0)


def mixed_suite():
    for mode in ["hay", "wood", "carrot"]:
        water = 0.1
        if mode == "hay":
            water = 0
        for size in [8, 32]:
            workers = 0
            if size == 8:
                workers = 1
            for seed in [1709, 8243]:
                trial("mix-base", mode, size, workers, seed, "mix-base", 2, water)
                trial("mix-new", mode, size, workers, seed, "mix", 2, water)
    trial("mix-existing", "hay", 8, 1, 8243, "mix-existing", 2, 0)
    trial("mix-budget", "hay", 8, 1, 1709, "mix-budget", 2, 0)


def mixed_rank_suite():
    for size in [8, 32]:
        for mode in ["hay", "wood", "carrot", "gold"]:
            trial("mixed-rank-full", mode, size, 0, 1709, "rank-full", 1, 0)


if SUITE == "all":
    small_suite()
    benchmark()
    tune()
    bones_suite()
    extras_suite()
    rank_suite()
    full_rank_suite()
    bone_bench()
    mixed_suite()
elif SUITE == "smoke":
    smoke()
elif SUITE == "suite":
    small_suite()
elif SUITE == "bench":
    benchmark()
elif SUITE == "bones":
    bones_suite()
    smoke()
elif SUITE == "bone-bench":
    bone_bench()
elif SUITE == "extras":
    extras_suite()
elif SUITE == "rank":
    rank_suite()
elif SUITE == "rank-full":
    full_rank_suite()
elif SUITE == "validation":
    extras_suite()
    rank_suite()
    bone_bench()
    smoke()
elif SUITE == "mix":
    mixed_suite()
elif SUITE == "mix-rank":
    mixed_rank_suite()
else:
    quick_print("[TEST] FAIL", "unknown suite", SUITE)
