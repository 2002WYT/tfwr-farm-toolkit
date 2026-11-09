from farm_route import go, parallel


# This implementation draws on public leaderboard results and experiments.
# https://github.com/enihsyou/The-Farmer-Was-Replaced
# https://github.com/Berman510/tfwr
# These strategies assume the starting field used by leaderboard simulations.


def _blocks(n, single, workers):
    if single or workers != 32 or n != 32:
        return [(0, n, 0, n)]
    blocks = []
    for y in range(0, n, 8):
        for x in range(0, n, 4):
            blocks.append((x, x + 4, y, y + 8))
    return blocks


def _cycle(bounds):
    # Traverse the interior in a serpentine path and reserve the west column for the return.
    x0, x1, y0, y1 = bounds
    route = []
    for y in range(y0, y1):
        if (y - y0) % 2 == 0:
            first = x0 + 1
            if y == y0:
                first = x0
            for x in range(first, x1 - 1):
                route.append(((x, y), East))
            route.append(((x1 - 1, y), North))
        else:
            for x in range(x1 - 1, x0 + 1, -1):
                route.append(((x, y), West))
            if y == y1 - 1:
                route.append(((x0 + 1, y), West))
            else:
                route.append(((x0 + 1, y), North))
    for y in range(y1 - 1, y0, -1):
        route.append(((x0, y), South))
    return route


def _surface(route, n):
    (x, y), direction = route[0]
    if not go(x, y, n):
        return False
    for point, direction in route:
        ground = get_ground_type()
        crop = get_entity_type()
        if (ground != Grounds.Grassland and ground != Grounds.Soil) or (crop != None and crop != Entities.Grass):
            return False
        if not move(direction):
            return False
    return True


def _dispatch(task, n, payloads):
    # Let each new drone launch half of the remaining blocks to shorten startup.
    count = len(payloads)
    if count == 1:
        return task(0, n, 1, payloads[0])
    half = count // 2
    first = []
    second = []
    for index in range(half):
        first.append(payloads[index])
    for index in range(half, count):
        second.append(payloads[index])
    child = spawn_drone(_dispatch, task, n, second)
    first_ok = _dispatch(task, n, first)
    if child == None:
        second_ok = _dispatch(task, n, second)
    else:
        second_ok = wait_for(child)
    return first_ok and second_ok


def _water(level):
    while get_water() < level and num_items(Items.Water) > 0:
        if not use_item(Items.Water):
            break


def _hay_points(bounds, variant):
    x0, x1, y0, y1 = bounds
    x = (x0 + x1) // 2 - 1
    y = (y0 + y1) // 2 - 1
    if variant == 1:
        return [((x, y), East), ((x + 1, y), North), ((x + 1, y + 1), West), ((x, y + 1), South)]
    return [((x, y), East), ((x + 1, y), West)]


def _hay(worker, n, workers, config):
    bounds, points, sources, target, variant = config
    if num_items(Items.Hay) >= target:
        return True
    route = _cycle(bounds)
    if not _surface(route, n):
        return False
    for point, direction in route:
        if point in sources:
            if get_ground_type() == Grounds.Soil:
                till()
        elif not plant(Entities.Bush):
            return False
        if not move(direction):
            return False
    (x, y), direction = points[0]
    if not go(x, y, n):
        return False

    level = 0.68
    if variant == 1:
        level = 0.44
    elif variant == 3:
        level = 0.76
    deadline = get_time() + 3600
    while num_items(Items.Hay) < target and get_time() < deadline:
        close = target - num_items(Items.Hay) < 2000000
        for point, direction in points:
            _water(level)
            if can_harvest():
                # With enough water, grass matures during the trip. Harvest it, then reroll the next request if needed.
                if not harvest():
                    return False
                if close and num_items(Items.Hay) >= target:
                    return True
                for attempt in range(36):
                    request = get_companion()
                    if request != None:
                        kind, position = request
                        if kind == Entities.Bush and position not in sources:
                            break
                    if not harvest():
                        break
            if not move(direction):
                return False
    return num_items(Items.Hay) >= target


def _source(point, crop, variant):
    x, y = point
    if crop == Entities.Carrot and variant > 1:
        return (x + 2 * y) % 4 == 0
    return (x + y) % 2 == 0


def _sow(crop, sources, bounds, reserved, irrigation, budget):
    x0, x1, y0, y1 = bounds
    if crop == Entities.Carrot and get_ground_type() == Grounds.Grassland:
        till()
    for attempt in range(24):
        if crop == Entities.Carrot:
            if budget == 0:
                return [False, None, budget]
            budget -= 1
        if not plant(crop):
            return [False, None, budget]
        request = get_companion()
        if request != None:
            kind, point = request
            x, y = point
            if (x0 <= x and x < x1 and y0 <= y and y < y1 and point not in sources
                    and kind != Entities.Carrot):
                if point not in reserved:
                    reserved[point] = [kind, 1]
                    _water(irrigation)
                    return [True, request, budget]
                claim = reserved[point]
                if claim[0] == kind:
                    claim[1] += 1
                    _water(irrigation)
                    return [True, request, budget]
        if attempt == 23 or (crop == Entities.Carrot and budget == 0):
            break
        # Remove only seedlings planted by this drone when rerolling the companion type and location.
        if not harvest():
            return [False, None, budget]
    _water(irrigation)
    return [True, None, budget]


def _install(kind):
    current = get_entity_type()
    if current == kind:
        return True
    if current != None and current != Entities.Grass and not harvest():
        return False
    if kind == Entities.Grass and get_ground_type() == Grounds.Grassland:
        return get_entity_type() == Entities.Grass
    return plant(kind)


def _pipeline(worker, n, workers, config):
    bounds, crop, output, target, irrigation, budget, variant = config
    if num_items(output) >= target:
        return True
    route = _cycle(bounds)
    if not _surface(route, n):
        return False

    sources = {}
    for point, direction in route:
        if _source(point, crop, variant):
            sources[point] = True

    active = {}
    reserved = {}
    installed = {}
    deadline = get_time() + 3600
    while num_items(output) < target and get_time() < deadline:
        for point, direction in route:
            if point in sources:
                sow = point not in active
                if not sow and can_harvest():
                    request = active[point]
                    ready = request == None
                    if request != None:
                        kind, helper = request
                        ready = helper in installed and installed[helper] == kind
                    if ready:
                        if not harvest():
                            return False
                        if num_items(output) >= target:
                            return True
                        active.pop(point)
                        if request != None:
                            claim = reserved[helper]
                            claim[1] -= 1
                            if claim[1] == 0:
                                reserved.pop(helper)
                        sow = True
                if sow:
                    if crop == Entities.Carrot and budget == 0:
                        # This drone has spent its seed budget. Other drones can keep producing.
                        if len(active) == 0:
                            return True
                    else:
                        ok, request, budget = _sow(crop, sources, bounds, reserved, irrigation, budget)
                        if not ok:
                            return False
                        active[point] = request
            elif point in reserved:
                kind = reserved[point][0]
                if point not in installed or installed[point] != kind:
                    if not _install(kind):
                        return False
                    installed[point] = kind
            if not move(direction):
                return False
    return num_items(output) >= target


def run_rank_poly(mode, single, target, variant=3):
    n = get_world_size()
    if variant < 1 or variant > 3 or target <= 0 or (single and n != 8) or (not single and n != 32):
        return False
    workers = 1
    if not single:
        workers = max_drones()
    blocks = _blocks(n, single, workers)
    workers = len(blocks)
    payloads = []
    if mode == "hay":
        output = Items.Hay
        task = _hay
        all_sources = {}
        for bounds in blocks:
            for point, direction in _hay_points(bounds, variant):
                all_sources[point] = True
        for bounds in blocks:
            payloads.append((bounds, _hay_points(bounds, variant), all_sources, target, variant))
    else:
        irrigation = 0.15
        budget = 0
        if mode == "wood":
            crop, output = Entities.Tree, Items.Wood
            if not single:
                irrigation = 0.35
            if variant == 2:
                irrigation = 0.70
            elif variant == 3:
                irrigation = 0.85
        elif mode == "carrot":
            crop, output = Entities.Carrot, Items.Carrot
            if variant == 2:
                irrigation = 0.50
            elif variant == 3:
                irrigation = 0.85
            cost = get_cost(crop)
            budget = 1000000000
            for item in cost:
                if cost[item] > 0:
                    budget = min(budget, num_items(item) // cost[item])
        else:
            return False
        task = _pipeline
        for worker in range(workers):
            share = (worker + 1) * budget // workers - worker * budget // workers
            payloads.append((blocks[worker], crop, output, target, irrigation, share, variant))

    if num_items(output) >= target:
        return True
    start = get_time()
    success = True
    if variant == 3 and workers > 1:
        success = _dispatch(task, n, payloads)
    else:
        for done in parallel(task, n, workers, payloads, True):
            success = success and done
    balance = num_items(output)
    quick_print("[RANK POLY]", mode, "variant", variant, "workers", workers,
                "seconds", get_time() - start, "balance", balance, "target", target)
    return success and balance >= target
