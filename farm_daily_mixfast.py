from farm_mix import run_mix
from farm_rank_poly import _blocks, _cycle
from farm_rank_poly_carrot import _pattern
from farm_rank_poly_fast import _hay_layout
from farm_route import go, parallel


def _inspect(worker, n, workers, main):
    occupied = False
    start = worker * n // workers
    for y in range(start, (worker + 1) * n // workers):
        if not go(0, y, n):
            return [False, occupied]
        for x in range(n):
            ground = get_ground_type()
            crop = get_entity_type()
            if ground != Grounds.Grassland and ground != Grounds.Soil:
                return [False, occupied]
            if (crop == main and main != Entities.Grass) or (crop == Entities.Grass and ground == Grounds.Soil):
                occupied = True
            elif crop != None and crop != Entities.Grass:
                return [False, occupied]
            if x + 1 < n and not move(East):
                return [False, occupied]
    return [True, occupied]


def _water(below, workers):
    if below > 0 and get_water() < below and num_items(Items.Water) >= workers:
        use_item(Items.Water)


def _hay_prep(worker, n, workers, config):
    bounds, pair, bushes = config
    planted = []
    tilled = []
    x0, x1, y0, y1 = bounds
    if not go(x0, y0, n):
        return [False, planted, tilled]
    for point, direction in _cycle(bounds):
        if point in pair or point in bushes:
            crop = get_entity_type()
            ground = get_ground_type()
            if (ground != Grounds.Soil and ground != Grounds.Grassland) or (crop != None and crop != Entities.Grass):
                return [False, planted, tilled]
            if point in pair:
                if ground == Grounds.Soil:
                    if crop != None:
                        return [False, planted, tilled]
                    till()
                    tilled.append(point)
            else:
                if not plant(Entities.Bush):
                    return [False, planted, tilled]
                planted.append(point)
        if not move(direction):
            return [False, planted, tilled]
    return [True, planted, tilled]


def _hay_harvest(worker, n, workers, config):
    pair, rounds, below = config
    x, y = pair[0]
    if not go(x, y, n):
        return [False, 0]
    directions = [East, West]
    laps = rounds * 8
    count = 0
    # 每对生产格每轮各收八次，保留原满编混种每轮 512 次成熟收获的口径。
    for lap in range(laps):
        for side in range(2):
            _water(below, workers)
            deadline = get_time() + 15
            while not can_harvest():
                if get_time() >= deadline:
                    return [False, count]
            if get_entity_type() != Entities.Grass or not harvest():
                return [False, count]
            count += 1
            if lap + 1 < laps:
                other = pair[1 - side]
                # 刚重生的草可重抽伴生；如果已成熟，留给下一次正式收割。
                for attempt in range(36):
                    request = get_companion()
                    if request != None and request[0] == Entities.Bush and request[1] != other:
                        break
                    if get_entity_type() != Entities.Grass or can_harvest() or not harvest():
                        break
            if not move(directions[side]):
                return [False, count]
    return [True, count]


def _hay_cleanup(worker, n, workers, config):
    planted, tilled = config
    ok = True
    for x, y in planted:
        if not go(x, y, n) or get_entity_type() != Entities.Bush or not harvest():
            ok = False
    for x, y in tilled:
        if go(x, y, n) and get_ground_type() == Grounds.Grassland:
            crop = get_entity_type()
            if crop == None or crop == Entities.Grass:
                till()
                continue
        ok = False
    return ok


def _run_hay(n, workers, rounds, below):
    blocks, pairs, bushes = _hay_layout(n, False)
    plant = []
    collect = []
    for index in range(workers):
        plant.append((blocks[index], pairs[index], bushes))
        collect.append((pairs[index], rounds, below))
    cleanup = []
    ok = True
    for ready, planted, tilled in parallel(_hay_prep, n, workers, plant, True):
        ok = ok and ready
        cleanup.append((planted, tilled))
    count = 0
    if ok:
        for ready, harvested in parallel(_hay_harvest, n, workers, collect, True):
            ok = ok and ready
            count += harvested
    # 灌木可能给相邻分区加成，所有生产结束后再移除脚本种下的灌木。
    for done in parallel(_hay_cleanup, n, workers, cleanup, True):
        ok = ok and done
    return [ok, count]


def _carrot_sow(helpers, claims, extra, below, workers):
    for attempt in range(24):
        if not plant(Entities.Carrot):
            return [False, extra, -2]
        request = get_companion()
        helper = -1
        if request != None:
            kind, point = request
            if point in helpers:
                index = helpers[point]
                claim = claims[index]
                if claim[1] == 0 or claim[0] == kind:
                    claim[0] = kind
                    claim[1] += 1
                    helper = index
        if helper >= 0 or extra == 0 or attempt == 23:
            _water(below, workers)
            return [True, extra, helper]
        # 只有预留的额外种子才用于换伴生，给剩余生产格保留一粒种子。
        if not harvest():
            return [False, extra, -2]
        extra -= 1
    return [False, extra, -2]


def _place_helper(kind, ground):
    crop = get_entity_type()
    if crop == kind:
        return True
    if crop != None and (crop != Entities.Grass or ground == Grounds.Soil):
        if not harvest():
            return False
    if kind == Entities.Grass and ground == Grounds.Grassland:
        return get_entity_type() == Entities.Grass
    return plant(kind)


def _carrot_cleanup(n, path, state):
    ok = True
    for x, y, direction, index in path:
        pending, claim, installed, original, remaining, tilled = state[index]
        if remaining < 0 and installed != None and (installed != Entities.Grass or original == Grounds.Soil):
            # 伴生植物由本机临时种植。生产结束后连同尚未成熟的伴生植物一起收掉。
            if not go(x, y, n) or get_entity_type() != installed or not harvest():
                ok = False
        if tilled:
            if go(x, y, n) and get_ground_type() == Grounds.Soil and get_entity_type() == None:
                till()
            else:
                ok = False
    return ok


def _carrot_worker(worker, n, workers, config):
    bounds, rounds, below, extra = config
    x0, x1, y0, y1 = bounds
    if not go(x0, y0, n):
        return [False, 0]
    pattern = _pattern(1)
    helpers = {}
    claims = []
    state = []
    path = []
    for point, direction in _cycle(bounds):
        x, y = point
        original = get_ground_type()
        crop = get_entity_type()
        if (original != Grounds.Soil and original != Grounds.Grassland) or (crop != None and crop != Entities.Grass):
            return [False, 0]
        if crop == Entities.Grass and original == Grounds.Soil:
            return [False, 0]
        index = len(path)
        remaining = rounds * 2
        if (x - x0, y - y0) not in pattern:
            remaining = -1
            helpers[point] = index
        claim = [None, 0]
        claims.append(claim)
        state.append([-2, claim, crop, original, remaining, False])
        path.append((x, y, direction, index))
        if not move(direction):
            return [False, 0]

    expected = rounds * 16
    count = 0
    ok = True
    deadline = get_time() + 90
    while ok and count < expected and get_time() < deadline:
        for x, y, direction, index in path:
            tile = state[index]
            helper, claim, installed, original, remaining, tilled = tile
            if remaining > 0:
                sow = helper == -2
                if not sow and can_harvest():
                    if helper == -1 or state[helper][2] == claims[helper][0]:
                        if not harvest():
                            ok = False
                            break
                        if helper >= 0:
                            claims[helper][1] -= 1
                        count += 1
                        tile[4] -= 1
                        tile[0] = -2
                        deadline = get_time() + 90
                        sow = tile[4] > 0
                if sow:
                    if original == Grounds.Grassland and not tilled:
                        till()
                        tile[5] = True
                    ok, extra, helper = _carrot_sow(helpers, claims, extra, below, workers)
                    if not ok:
                        break
                    tile[0] = helper
            elif remaining < 0 and claim[1] > 0 and installed != claim[0]:
                if not _place_helper(claim[0], original):
                    tile[2] = get_entity_type()
                    ok = False
                    break
                tile[2] = claim[0]
            if not move(direction):
                ok = False
                break
    cleaned = _carrot_cleanup(n, path, state)
    return [ok and cleaned and count == expected, count]


def run_daily_mixfast(mode, rounds, workers, water_below):
    if rounds < 1 or rounds % 1 != 0 or workers < 0 or workers % 1 != 0 or water_below < 0 or water_below > 1:
        return False
    if mode == "hay":
        crop, output = Entities.Grass, Items.Hay
    elif mode == "carrot":
        crop, output = Entities.Carrot, Items.Carrot
    else:
        return False
    n = get_world_size()
    active = workers
    if active == 0:
        active = max_drones()
    active = min(n, active, max_drones())
    start = get_time()
    before = num_items(output)
    occupied = False
    for ok, previous in parallel(_inspect, n, active, crop):
        if not ok:
            quick_print("[MIX DAILY STOP]", "foreign crop or non-surface ground", mode)
            return False
        occupied = occupied or previous
    if (n != 32 or active != 32 or occupied or num_unlocked(crop) == 0
            or num_unlocked(Unlocks.Polyculture) == 0):
        return run_mix(mode, rounds, workers, water_below)
    if num_unlocked(Unlocks.Watering) == 0:
        water_below = 0

    expected = rounds * 512
    if mode == "hay":
        ok, count = _run_hay(n, active, rounds, water_below)
    else:
        budget = expected * 4
        cost = get_cost(crop)
        for item in cost:
            if cost[item] > 0:
                budget = min(budget, num_items(item) // cost[item])
        if budget < expected:
            quick_print("[MIX DAILY STOP]", "carrot seed budget", "have", budget, "need", expected)
            return False
        extra = budget - expected
        if extra < expected // 2:
            return run_mix(mode, rounds, workers, water_below)
        payloads = []
        for bounds in _blocks(n, False, active):
            index = len(payloads)
            share = (index + 1) * extra // active - index * extra // active
            payloads.append((bounds, rounds, water_below, share))
        ok = True
        count = 0
        for done, harvested in parallel(_carrot_worker, n, active, payloads, True):
            ok = ok and done
            count += harvested

    elapsed = get_time() - start
    gain = num_items(output) - before
    ok = ok and count == expected and gain > 0
    quick_print("[MIX DAILY]", mode, "ok", ok, "rounds", rounds, "harvest_actions", count,
                "expected", expected, "gain", gain, "seconds", elapsed)
    if elapsed > 0:
        quick_print("[RATE]", output, "net_per_min", gain * 60 / elapsed)
    return ok
