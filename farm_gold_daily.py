from farm_gold import gold_geometry, gold_surface, run_gold
from farm_rank_maze import rank_maze_worker
from farm_route import go, parallel


def run_gold_daily(rounds, workers):
    n = get_world_size()
    level = num_unlocked(Unlocks.Mazes)
    if rounds < 1 or rounds % 1 != 0 or workers < 0 or workers % 1 != 0 or level == 0:
        quick_print("[GOLD DAILY STOP]", "requires maze research and whole-number rounds and workers")
        return False
    if num_unlocked(Unlocks.Megafarm) > 0 and num_drones() != 1:
        quick_print("[GOLD DAILY STOP]", "finish the other drones before starting")
        return False

    layout = gold_geometry(n, workers)
    active = layout[0]
    grid = layout[1]
    side = n // grid
    if side < 2 or (active == 1 and n != 8):
        # Bidirectional search was tested on 8×8 single-drone fields. Other sizes use the baseline.
        quick_print("[GOLD DAILY]", "standard layout", "size", n, "workers", active)
        return run_gold(rounds, workers)

    substance = side * 2 ** (level - 1)
    expected_pickups = rounds * active
    expected_cost = expected_pickups * substance
    before_substance = num_items(Items.Weird_Substance)
    if before_substance < expected_cost:
        # Dense mazes can cost more Weird Substance per chest. Choose the corridor layout before starting if needed.
        quick_print("[GOLD DAILY]", "standard layout", "dense cost", expected_cost,
                    "available", before_substance)
        return run_gold(rounds, workers)

    started = get_time()
    before_gold = num_items(Items.Gold)
    for clean in parallel(gold_surface, n, min(n, active), None):
        if not clean:
            quick_print("[GOLD DAILY STOP]", "surface must contain only empty ground and grass")
            return False
    if not go(0, 0, n):
        return False

    start_at = get_time()
    if active > 1:
        # Let every drone reach its planting tile before creating mazes. Allow for travel without power.
        measured_at = get_time()
        if not move(East):
            return False
        action_time = get_time() - measured_at
        if not move(West) or action_time <= 0:
            return False
        start_at = get_time() + (n + active + 8) * action_time * 2

    collected = 0
    # A zero final argument gives each drone its own round limit.
    config = (rounds, grid, side, substance, start_at, 3, 0)
    for pickups in parallel(rank_maze_worker, n, active, config):
        collected += pickups
    gain = num_items(Items.Gold) - before_gold
    spent = before_substance - num_items(Items.Weird_Substance)
    elapsed = get_time() - started
    expected_gold = expected_cost * side
    quick_print("[GOLD DAILY]", "maze_side", side, "workers", active, "rounds", rounds,
                "pickups", collected, "gold", gain, "expected", expected_gold,
                "substance", spent, "seconds", elapsed)
    if elapsed > 0:
        quick_print("[RATE]", Items.Gold, "net_per_min", gain * 60 / elapsed)
    if collected != expected_pickups or gain != expected_gold or spent != expected_cost:
        quick_print("[GOLD DAILY STOP]", "incomplete maze batch")
        return False
    return True
