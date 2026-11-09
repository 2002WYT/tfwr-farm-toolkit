from farm_rank_candidate import candidate
from farm_rank_core import rank_profile
from farm_daily_crops import run_power_daily, run_pumpkin_daily
from farm_daily_fast import run_bones_daily, run_cactus_daily
from farm_daily_mixfast import run_daily_mixfast
from farm_daily_poly import run_wood_daily
from farm_gold_daily import run_gold_daily
from farm_mix import run_mix
from farm_ops import run


def probe_daily(item):
    workers = 0
    if single:
        workers = 1
    rounds = 2
    if mode == "bone":
        rounds = 1
    elif mode == "wood":
        rounds = 10
    elif mode == "pumpkin" or mode == "power":
        rounds = 3
    if mode == "gold":
        rounds = 100
        if variant <= -4:
            rounds = 301
    before = num_items(item)
    started = get_time()
    if mode == "hay" or mode == "carrot":
        irrigation = 0
        if variant <= -6:
            irrigation = 0.1
        if variant == -1 or variant == -6:
            ok = run_mix(mode, rounds, workers, irrigation)
        else:
            ok = run_daily_mixfast(mode, rounds, workers, irrigation)
    elif mode == "wood":
        if variant == -1:
            ok = run_mix(mode, rounds, workers, 0)
        else:
            ok = run_wood_daily(rounds, workers, 0)
    elif variant == -1 or variant == -4:
        ok = run(mode, rounds, workers, 0)
    elif mode == "gold":
        ok = run_gold_daily(rounds, workers)
    elif mode == "bone":
        ok = run_bones_daily(rounds, variant == -3)
    elif mode == "pumpkin":
        ok = run_pumpkin_daily(rounds, workers, 0)
    elif mode == "power":
        ok = run_power_daily(rounds, workers, 0)
    else:
        cactus_variant = 3
        if variant == -3:
            cactus_variant = 4
        ok = run_cactus_daily(rounds, workers, 0, cactus_variant)
    elapsed = get_time() - started
    gain = num_items(item) - before
    quick_print("[DAILY]", mode, "single", single, "variant", variant, "seed", seed,
                "seconds", elapsed, "gain", gain, "net_per_min", gain * 60 / elapsed, "passed", ok and gain > 0)


def probe():
    size = 32
    if single:
        size = 8
    set_world_size(size)
    leaderboard, item, goal, water = rank_profile(mode, single)
    if variant < 0:
        probe_daily(item)
        return
    started = get_time()
    ok = candidate(mode, single, variant)
    elapsed = get_time() - started
    amount = num_items(item)
    quick_print("[LAB]", mode, "single", single, "variant", variant, "seed", seed,
                "seconds", elapsed, "output", amount, "goal", goal, "passed", ok and amount >= goal)


probe()
