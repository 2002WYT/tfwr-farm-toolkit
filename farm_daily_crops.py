from farm_ops import inspect_worker, run
from farm_rank_crop_power import _bounds, _nearest
from farm_route import go, parallel


def _active(workers, n):
    if workers == 0:
        workers = max_drones()
    return min(workers, n, max_drones())


def _valid(rounds, workers, water):
    return (rounds >= 1 and rounds % 1 == 0 and workers >= 0
            and workers % 1 == 0 and water >= 0 and water <= 1)


def _surface(crop, n, active):
    occupied = 0
    for ok, found in parallel(inspect_worker, n, active, (crop, False)):
        if not ok:
            quick_print("[CROP DAILY STOP]", "foreign crop or non-surface ground")
            return False, occupied
        occupied += found
    return True, occupied


def _water(below, active):
    # 每架机最多同时补一桶，库存不足时等自然生长。
    if below > 0 and get_water() < below and num_items(Items.Water) >= active:
        use_item(Items.Water)


def _sow(crop, water, active):
    if not plant(crop):
        return False
    _water(water, active)
    return True


def _pumpkin_part(n, x, y, begin, end, water, active):
    pending = []
    for index in range(begin, end):
        row = index // 7
        column = index % 7
        tx = x + column
        ty = y + row
        direction = East
        if row % 2 == 1:
            tx = x + 6 - column
            direction = West
        if index == begin and not go(tx, ty, n):
            return False
        if get_ground_type() != Grounds.Soil:
            till()
        if not _sow(Entities.Pumpkin, water, active):
            return False
        pending.append((tx, ty))
        if index + 1 < end:
            if column == 6:
                direction = North
            if not move(direction):
                return False

    deadline = get_time() + 30
    while len(pending) > 0:
        remaining = []
        for tx, ty in pending:
            if not go(tx, ty, n):
                return False
            if not can_harvest():
                if get_entity_type() == Entities.Dead_Pumpkin:
                    if not _sow(Entities.Pumpkin, water, active):
                        return False
                remaining.append((tx, ty))
        pending = remaining
        if get_time() >= deadline and len(pending) > 0:
            return False
    return True


def _pumpkin_worker(worker, n, workers, config):
    batches, water, active = config
    x = worker % 4 * 8
    y = worker // 4 * 8
    count = batches // workers
    if worker < batches % workers:
        count += 1
    collected = 0
    for batch in range(count):
        # 每块独立收获。留一格隔开各块，两机分担 24 和 25 格。
        child = spawn_drone(_pumpkin_part, n, x, y, 24, 49, water, active)
        if child == None:
            ok = _pumpkin_part(n, x, y, 0, 49, water, active)
        else:
            ok = _pumpkin_part(n, x, y, 0, 24, water, active)
            if ok:
                ok = go(x, y, n)
            ok = wait_for(child) and ok
        if not ok or not can_harvest() or not harvest():
            break
        collected += 1
    return collected


def run_pumpkin_daily(rounds, workers, water_below):
    if not _valid(rounds, workers, water_below):
        return False
    n = get_world_size()
    active = _active(workers, n)
    level = num_unlocked(Unlocks.Pumpkins)
    if n != 32 or active != 32 or level == 0:
        return run("pumpkin", rounds, workers, water_below)
    if num_drones() != 1:
        return False
    if num_unlocked(Unlocks.Watering) == 0:
        water_below = 0

    # 每个分区按同样的单格倍率产出，补足整田轮数对应的最低产量。
    patches = (rounds * n * n + 48) // 49
    cost = get_cost(Entities.Pumpkin)
    for item in cost:
        if num_items(item) < patches * 49 * cost[item]:
            return run("pumpkin", rounds, workers, water_below)
    started = get_time()
    ok, occupied = _surface(Entities.Pumpkin, n, active)
    if not ok:
        return False
    if occupied > 0:
        return run("pumpkin", rounds, workers, water_below)

    before = num_items(Items.Pumpkin)
    collected = 0
    for count in parallel(_pumpkin_worker, n, 16, (patches, water_below, active)):
        collected += count
    gain = num_items(Items.Pumpkin) - before
    expected = patches * 49 * 6 * 2 ** (level - 1)
    elapsed = get_time() - started
    quick_print("[PUMPKIN DAILY]", "rounds", rounds, "patches", collected, "gain", gain,
                "expected", expected, "seconds", elapsed)
    if elapsed > 0:
        quick_print("[RATE]", Items.Pumpkin, "net_per_min", gain * 60 / elapsed)
    return collected == patches and gain == expected


def _wait_mature(deadline):
    while not can_harvest():
        if get_time() >= deadline:
            return False
    return True


def _flower_marker(x, y, at_flower, n, deadline):
    if not at_flower and not go(x, y, n):
        return False
    current = get_entity_type()
    if current == None or current == Entities.Dead_Pumpkin:
        if not plant(Entities.Grass):
            return False
    elif current != Entities.Grass:
        return False
    return _wait_mature(deadline) and harvest()


def _flower_worker(worker, n, workers, config):
    water, carrots_done, hay_start, signal_gain, deadline = config
    left, right, bottom, top = _bounds(worker, n, workers)
    mark_x = (left + right) // 2
    mark_y = (bottom + top) // 2
    flowers = [[], [], [], [], [], [], [], [], []]
    if not go(left, bottom, n):
        return False
    for y in range(bottom, top):
        direction = East
        if (y - bottom) % 2 == 1:
            direction = West
        for column in range(right - left):
            x = left + column
            if direction == West:
                x = right - 1 - column
            if x != mark_x or y != mark_y:
                if get_ground_type() != Grounds.Soil:
                    till()
                if not _sow(Entities.Sunflower, water, workers):
                    return False
                flowers[measure() - 7].append((x, y))
            if column + 1 < right - left and not move(direction):
                return False
        if y + 1 < top and not move(North):
            return False

    while num_items(Items.Carrot) > carrots_done:
        if get_time() >= deadline:
            return False
    for petals in range(8, -1, -1):
        points = flowers[petals]
        count = len(points)
        while len(points) > 0:
            x, y = _nearest(points, n)
            if not go(x, y, n) or not _wait_mature(deadline) or not harvest():
                return False
        if petals > 0:
            # 正常收草作为各档信号，不翻动标记格的地面。
            if not _flower_marker(mark_x, mark_y, count > 0, n, deadline):
                return False
            barrier = hay_start + (9 - petals) * workers * signal_gain
            while num_items(Items.Hay) < barrier:
                if get_time() >= deadline:
                    return False
    return True


def run_power_daily(rounds, workers, water_below):
    if not _valid(rounds, workers, water_below):
        return False
    n = get_world_size()
    active = _active(workers, n)
    grass_level = num_unlocked(Unlocks.Grass)
    if n != 32 or active != 32 or grass_level == 0 or num_unlocked(Entities.Sunflower) == 0:
        return run("power", rounds, workers, water_below)
    if num_drones() != 1:
        return False
    if num_unlocked(Unlocks.Watering) == 0:
        water_below = 0
    cost = get_cost(Entities.Sunflower)
    if len(cost) != 1 or Items.Carrot not in cost or cost[Items.Carrot] <= 0:
        return run("power", rounds, workers, water_below)

    started = get_time()
    ok, occupied = _surface(Entities.Sunflower, n, active)
    if not ok:
        return False
    if occupied > 0:
        return run("power", rounds, workers, water_below)
    before = num_items(Items.Power)
    carrot_cost = (n * n - active) * cost[Items.Carrot]
    signal_gain = 2 ** (grass_level - 1)
    for batch in range(rounds):
        carrots = num_items(Items.Carrot)
        if carrots < carrot_cost:
            return False
        args = (water_below, carrots - carrot_cost, num_items(Items.Hay),
                signal_gain, get_time() + 90)
        for ok in parallel(_flower_worker, n, active, args):
            if not ok:
                return False
    gain = num_items(Items.Power) - before
    elapsed = get_time() - started
    quick_print("[POWER DAILY]", "rounds", rounds, "flowers", rounds * (n * n - active),
                "gain", gain, "seconds", elapsed)
    if elapsed > 0:
        quick_print("[RATE]", Items.Power, "net_per_min", gain * 60 / elapsed)
    return gain > 0
