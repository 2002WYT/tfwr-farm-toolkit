from farm_mix import run_mix
from farm_route import go, parallel


def _inspect(worker, n, workers, unused):
    occupied = False
    soil = []
    first = worker * n // workers
    for y in range(first, (worker + 1) * n // workers):
        start = 0
        step = 1
        direction = East
        if (y - first) % 2 == 1:
            start = n - 1
            step = -1
            direction = West
        if not go(start, y, n):
            return [False, occupied, soil]
        for column in range(n):
            if column > 0 and not move(direction):
                return [False, occupied, soil]
            ground = get_ground_type()
            crop = get_entity_type()
            if ground != Grounds.Grassland and ground != Grounds.Soil:
                return [False, occupied, soil]
            if crop == Entities.Tree or crop == Entities.Bush or (crop == Entities.Grass and ground == Grounds.Soil):
                occupied = True
            elif crop != None and crop != Entities.Grass:
                return [False, occupied, soil]
            x = start + column * step
            if crop == None and ground == Grounds.Soil and (x + y) % 2 == 1:
                soil.append((x, y))
    return [True, occupied, soil]


def _change_soil(worker, n, workers, config):
    if len(config) == 0:
        return [True, []]
    points, original = config
    ok = True
    changed = []
    for x, y in points:
        if not go(x, y, n) or get_ground_type() != original:
            ok = False
            continue
        crop = get_entity_type()
        if crop != None and (crop != Entities.Grass or original == Grounds.Soil):
            ok = False
            continue
        till()
        changed.append((x, y))
    return [ok, changed]


def _wood_cycle(worker):
    # 每台无人机走一个 4×8 闭环，最后沿左侧一列返回起点。
    x0, y0 = worker % 8 * 4, worker // 8 * 8
    path = [(x0, y0, East)]
    for y in range(y0, y0 + 8):
        if y % 2 == 0:
            path.append((x0 + 1, y, East))
            path.append((x0 + 2, y, East))
            path.append((x0 + 3, y, North))
        else:
            path.append((x0 + 3, y, West))
            path.append((x0 + 2, y, West))
            turn = North
            if y == y0 + 7:
                turn = West
            path.append((x0 + 1, y, turn))
    for y in range(y0 + 7, y0, -1):
        path.append((x0, y, South))
    return path


def _plant_tree(water_below):
    for attempt in range(40):
        if not plant(Entities.Tree):
            return False
        request = get_companion()
        if request != None:
            kind, (x, y) = request
            if kind == Entities.Grass and (x + y) % 2 == 1:
                break
        if attempt < 39 and not harvest():
            return False
    if water_below > 0 and get_water() < water_below and num_items(Items.Water) > 0:
        use_item(Items.Water)
    return True


def _harvest_wood(worker, n, workers, config):
    rounds, water_below = config
    route = _wood_cycle(worker)
    x0, y0, direction = route[0]
    if not go(x0, y0, n):
        return [False, 0]
    remaining = []
    for x, y, direction in route:
        if (x + y) % 2 == 0:
            remaining.append(rounds)
        else:
            remaining.append(0)

    harvested = 0
    expected = rounds * 16
    deadline = get_time() + 90
    while harvested < expected and get_time() < deadline:
        for index in range(len(route)):
            x, y, direction = route[index]
            if remaining[index] > 0:
                crop = get_entity_type()
                sow = crop == None or crop == Entities.Grass
                if crop == Entities.Tree:
                    if can_harvest():
                        if not harvest():
                            return [False, harvested]
                        harvested += 1
                        remaining[index] -= 1
                        deadline = get_time() + 90
                        sow = remaining[index] > 0
                elif not sow:
                    return [False, harvested]
                # 最后一轮成熟树收完即停，避免留下额外的树苗。
                if sow and not _plant_tree(water_below):
                    return [False, harvested]
            if harvested == expected:
                return [True, harvested]
            if not move(direction):
                return [False, harvested]
    return [harvested == expected, harvested]


def run_wood_daily(rounds, workers, water_below):
    if rounds < 1 or rounds % 1 != 0 or workers < 0 or workers % 1 != 0 or water_below < 0 or water_below > 1:
        quick_print("[WOOD DAILY STOP]", "invalid configuration")
        return False
    n = get_world_size()
    active = workers
    if active == 0:
        active = max_drones()
    active = min(n, active, max_drones())
    started = get_time()
    before = num_items(Items.Wood)
    occupied = False
    work = []
    has_soil = False
    for ok, old_crop, soil in parallel(_inspect, n, active, None):
        if not ok:
            quick_print("[WOOD DAILY STOP]", "foreign crop, inaccessible tile or non-surface ground")
            return False
        occupied = occupied or old_crop
        if len(soil) > 0:
            work.append((soil, Grounds.Soil))
            has_soil = True
        else:
            work.append([])

    if (n != 32 or active != 32 or occupied or num_unlocked(Unlocks.Trees) == 0
            or num_unlocked(Unlocks.Polyculture) == 0):
        quick_print("[WOOD DAILY]", "legacy mixed route", "size", n, "workers", active, "existing_crop", occupied)
        return run_mix("wood", rounds, workers, water_below)
    if num_unlocked(Unlocks.Watering) == 0:
        water_below = 0

    ok = True
    restore = []
    if has_soil:
        # 跨区伴生草会被所有无人机使用，先全部准备，最后再全部恢复。
        for ready, changed in parallel(_change_soil, n, active, work, True):
            ok = ok and ready
            if len(changed) > 0:
                restore.append((changed, Grounds.Grassland))
            else:
                restore.append([])
    harvested = 0
    if ok:
        for done, count in parallel(_harvest_wood, n, active, (rounds, water_below)):
            ok = ok and done
            harvested += count
    if has_soil:
        for done, changed in parallel(_change_soil, n, active, restore, True):
            ok = ok and done

    expected = rounds * n * n // 2
    elapsed = get_time() - started
    gain = num_items(Items.Wood) - before
    ok = ok and harvested == expected and gain > 0
    quick_print("[WOOD DAILY]", "ok", ok, "size", n, "workers", active, "rounds", rounds,
                "harvest_actions", harvested, "expected", expected, "wood", gain, "seconds", elapsed)
    if elapsed > 0:
        quick_print("[RATE]", Items.Wood, "net_per_min", gain * 60 / elapsed)
    return ok
