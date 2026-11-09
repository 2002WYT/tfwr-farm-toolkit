from farm_bones import empty_stripe, run_bones
from farm_gold_daily import run_gold_daily
from farm_ops import inspect_worker, run
from farm_rank_bone import rank_tail, run_rank_bone
from farm_rank_crop_cactus import rank_cactus
from farm_route import parallel


def run_cactus_daily(rounds, workers, water_below, variant=3):
    n = get_world_size()
    level = num_unlocked(Unlocks.Cactus)
    active = workers
    if workers == 0:
        active = max_drones()
    active = min(n, active, max_drones())
    if (rounds < 1 or rounds % 1 != 0 or level == 0 or water_below != 0
            or not ((n == 8 and active == 1) or (n == 32 and active == 32))):
        return run("cactus", rounds, workers, water_below)

    started = get_time()
    for ok, occupied in parallel(inspect_worker, n, active, (Entities.Cactus, False)):
        if not ok:
            quick_print("[CACTUS DAILY STOP]", "foreign crop or non-surface ground")
            return False
        if occupied > 0:
            # Use the baseline to finish existing cactus plants that may have different growth times.
            return run("cactus", rounds, workers, water_below)

    before = num_items(Items.Cactus)
    expected = rounds * n ** 4 * 2 ** (level - 1)
    ok = rank_cactus(active == 1, before + expected, variant)
    gain = num_items(Items.Cactus) - before
    elapsed = get_time() - started
    quick_print("[CACTUS DAILY]", "variant", variant, "size", n, "workers", active,
                "rounds", rounds, "gain", gain, "expected", expected, "seconds", elapsed)
    if elapsed > 0:
        quick_print("[RATE]", Items.Cactus, "net_per_min", gain * 60 / elapsed)
    return ok and gain == expected


def run_gold_preferred(rounds, workers):
    n = get_world_size()
    active = 1
    if num_unlocked(Unlocks.Megafarm) > 0:
        active = max_drones()
    if workers > 0:
        active = min(active, workers)
    # Dense packing has a higher setup cost. Use it on 8×8 single-drone fields or long runs with all drones.
    if (n == 8 and active == 1) or (n == 32 and active == 32 and rounds >= 301):
        return run_gold_daily(rounds, workers)
    return run("gold", rounds, workers, 0)


def _daily_bone_tail(n, goal, directions, runs):
    return rank_tail(n, goal, directions, runs, 4)


def run_bones_daily(rounds, rail=False):
    n = get_world_size()
    level = num_unlocked(Unlocks.Dinosaurs)
    if n != 32 or level == 0 or rounds < 1 or rounds % 1 != 0:
        return run_bones(rounds, True)
    # If stock only supports part of a tail, use the safe cycle for the available apples.
    if not rail:
        return run_bones(rounds, True, True, [_daily_bone_tail])
    cost = get_cost(Entities.Apple)
    length = n * n - 1
    full_batches = rounds
    for item in cost:
        if cost[item] > 0:
            full_batches = min(full_batches, num_items(item) // (length * cost[item]))
    if full_batches == 0:
        return run_bones(rounds, True, True, [_daily_bone_tail])
    for clean in parallel(empty_stripe, n, min(n, max_drones()), None):
        if not clean:
            quick_print("[BONE DAILY STOP]", "surface must be empty or grass")
            return False
    expected = length ** 2 * 2 ** (level - 1)
    for batch in range(1, full_batches + 1):
        start = get_time()
        before = num_items(Items.Bone)
        ok = run_rank_bone(before + expected, 8)
        gain = num_items(Items.Bone) - before
        elapsed = get_time() - start
        quick_print("[BONE DAILY]", "batch", batch, "bone", gain, "expected", expected, "seconds", elapsed)
        if elapsed > 0:
            quick_print("[RATE]", Items.Bone, "net_per_min", gain * 60 / elapsed)
        if not ok or gain != expected:
            return False
    if full_batches < rounds:
        return run_bones(rounds - full_batches, True, True, [_daily_bone_tail])
    return True
