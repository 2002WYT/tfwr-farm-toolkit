from farm_route import go
from farm_rank_poly import _blocks, _cycle, _dispatch, _install, _surface


# 独立实现。干草双格思路参考 https://github.com/enihsyou/The-Farmer-Was-Replaced
# 只用于榜单模拟，正常生产继续使用 farm_mix。


def _water_to(level):
    water = get_water()
    if water < level:
        count = -((water - level) * 4 // 1)
        count = min(count, num_items(Items.Water))
        if count > 0:
            use_item(Items.Water, count)


def _hay_layout(n, single):
    blocks = [(0, n, 0, n)]
    if not single:
        blocks = []
        for y in range(0, n, 4):
            for x in range(0, n, 8):
                blocks.append((x, x + 8, y, y + 4))
    pairs = []
    sources = {}
    for x0, x1, y0, y1 in blocks:
        x, y = (x0 + x1) // 2 - 1, (y0 + y1) // 2 - 1
        pair = ((x, y), (x + 1, y))
        pairs.append(pair)
        sources[pair[0]] = True
        sources[pair[1]] = True
    # 仅种草可选中的格子。每对草与其他对至少隔四格，唯一冲突是本对的另一格。
    bushes = {}
    for x, y in sources:
        for dy in range(-3, 4):
            width = 3 - abs(dy)
            for dx in range(-width, width + 1):
                point = ((x + dx) % n, (y + dy) % n)
                if point not in sources:
                    bushes[point] = True
    return [blocks, pairs, bushes]


def _prepare_hay(n, bounds, pair, bushes):
    x0, x1, y0, y1 = bounds
    if n % 2 == 1:
        # 5×5 单机的奇数边不能套用偶数行闭环，直接访问每个伴生点。
        for x, y in bushes:
            if not go(x, y, n) or not plant(Entities.Bush):
                return False
        x, y = pair[0]
        return go(x, y, n)
    if not go(x0, y0, n):
        return False
    for point, direction in _cycle(bounds):
        if point in bushes or point in pair:
            current = get_entity_type()
            ground = get_ground_type()
            if (current != None and current != Entities.Grass) or (ground != Grounds.Soil and ground != Grounds.Grassland):
                return False
            if point in pair:
                if ground == Grounds.Soil:
                    till()
            elif not plant(Entities.Bush):
                return False
        if not move(direction):
            return False

    x, y = pair[0]
    return go(x, y, n)


def _hay_pair(worker, n, workers, config):
    bounds, pair, bushes, target, variant = config
    if not _prepare_hay(n, bounds, pair, bushes):
        return False
    level = 0.68
    if variant == 2:
        level = 0.82
    deadline = get_time() + 3600
    directions = [East, West]
    while num_items(Items.Hay) < target and get_time() < deadline:
        for side in range(2):
            _water_to(level)
            # 等待本株成熟，省去来回空走，也保留已经选中的伴生偏好。
            while not can_harvest():
                if get_time() >= deadline:
                    return False
            if not harvest():
                return False
            if num_items(Items.Hay) >= target:
                return True
            other = pair[1 - side]
            for attempt in range(36):
                request = get_companion()
                if request != None:
                    kind, point = request
                    if kind == Entities.Bush and point != other:
                        break
                if not harvest():
                    break
            if not move(directions[side]):
                return False
    return num_items(Items.Hay) >= target


def _hay_pair_quick(worker, n, workers, config):
    bounds, pair, bushes, target, variant = config
    if not _prepare_hay(n, bounds, pair, bushes):
        return False
    directions = [East, West]
    partners = [pair[1], pair[0]]
    threshold = 0.69
    if variant == 4:
        threshold = 0.66
    for lap in range(10000):
        for side in range(2):
            moisture = get_water()
            if moisture < threshold and num_items(Items.Water) > 16:
                if use_item(Items.Water):
                    moisture += 0.25
            # 湿润时，两次走位与对格的收割已经给草留出了成熟时间。
            if moisture < 0.65:
                while not can_harvest():
                    pass
            if not harvest():
                return False
            if num_items(Items.Hay) >= target:
                return True
            other = partners[side]
            for attempt in range(36):
                request = get_companion()
                if request != None and request[0] == Entities.Bush and request[1] != other:
                    break
                if not harvest():
                    break
            if not move(directions[side]):
                return False
    return num_items(Items.Hay) >= target


def _wood_static(worker, n, workers, config):
    bounds, target, level = config
    route = _cycle(bounds)
    if not _surface(route, n):
        return False
    # 全田的奇数格始终是草地，因此允许树选择其他无人机区域的伴生草。
    for point, direction in route:
        x, y = point
        if (x + y) % 2 == 1 and get_ground_type() == Grounds.Soil:
            till()
        if not move(direction):
            return False

    deadline = get_time() + 3600
    while num_items(Items.Wood) < target and get_time() < deadline:
        for point, direction in route:
            x, y = point
            if (x + y) % 2 == 0:
                current = get_entity_type()
                ready = current != Entities.Tree
                if not ready and can_harvest():
                    if not harvest():
                        return False
                    if num_items(Items.Wood) >= target:
                        return True
                    ready = True
                if ready:
                    for attempt in range(40):
                        if not plant(Entities.Tree):
                            return False
                        request = get_companion()
                        if request != None:
                            kind, (cx, cy) = request
                            if kind == Entities.Grass and (cx + cy) % 2 == 1:
                                break
                        if attempt < 39 and not harvest():
                            return False
                    _water_to(level)
            if not move(direction):
                return False
    return num_items(Items.Wood) >= target


def _carrot_flex(worker, n, workers, config):
    bounds, target, budget, level, variant = config
    x0, x1, y0, y1 = bounds
    route = _cycle(bounds)
    if not _surface(route, n):
        return False
    sources = {}
    requests = {}
    planted_helpers = {}
    deadline = get_time() + 3600
    limit = 12
    if variant == 2:
        limit = 8
    while num_items(Items.Carrot) < target and get_time() < deadline:
        for point, direction in route:
            if point in requests:
                claim = requests[point]
                if point not in planted_helpers or planted_helpers[point] != claim[0]:
                    if not _install(claim[0]):
                        return False
                    planted_helpers[point] = claim[0]
            else:
                sow = point not in sources
                if not sow and can_harvest():
                    kind, helper = sources[point]
                    if helper == None or (helper in planted_helpers and planted_helpers[helper] == kind):
                        if not harvest():
                            return False
                        if num_items(Items.Carrot) >= target:
                            return True
                        sources.pop(point)
                        if helper != None:
                            claim = requests[helper]
                            claim[1] -= 1
                            if claim[1] == 0:
                                requests.pop(helper)
                        sow = True
                if sow and budget > 0:
                    if point in planted_helpers:
                        planted_helpers.pop(point)
                        current = get_entity_type()
                        if current != None and not harvest():
                            return False
                    if get_ground_type() != Grounds.Soil:
                        till()
                    for attempt in range(limit):
                        if not plant(Entities.Carrot):
                            return False
                        budget -= 1
                        request = get_companion()
                        if request != None:
                            kind, helper = request
                            x, y = helper
                            if x0 <= x and x < x1 and y0 <= y and y < y1 and helper not in sources:
                                if helper not in requests:
                                    requests[helper] = [kind, 1]
                                    sources[point] = (kind, helper)
                                    break
                                claim = requests[helper]
                                if claim[0] == kind:
                                    claim[1] += 1
                                    sources[point] = (kind, helper)
                                    break
                        if budget == 0:
                            sources[point] = (None, None)
                            break
                        if not harvest():
                            return False
                    if point in sources:
                        _water_to(level)
                elif sow and len(sources) == 0:
                    return True
            if not move(direction):
                return False
    return num_items(Items.Carrot) >= target


def run_rank_poly_fast(mode, single, target, variant=1):
    n = get_world_size()
    if target <= 0 or variant < 1 or variant > 4 or (single and n != 8) or (not single and n != 32):
        return False
    if mode == "hay" and single and variant >= 3:
        set_world_size(5)
        n = get_world_size()
    workers = 1
    if not single:
        workers = max_drones()
        if workers < 32:
            return False
        workers = 32
    blocks = _blocks(n, single, workers)
    payloads = []
    if mode == "hay":
        output = Items.Hay
        task = _hay_pair
        if variant >= 3:
            task = _hay_pair_quick
        blocks, pairs, bushes = _hay_layout(n, single)
        for index in range(len(blocks)):
            payloads.append((blocks[index], pairs[index], bushes, target, variant))
    elif mode == "wood":
        output = Items.Wood
        task = _wood_static
        level = 0.34
        if variant == 2:
            level = 0.62
        for bounds in blocks:
            payloads.append((bounds, target, level))
    elif mode == "carrot":
        output = Items.Carrot
        task = _carrot_flex
        level = 0.72
        if variant == 2:
            level = 0.55
        cost = get_cost(Entities.Carrot)
        budget = 1000000000
        for item in cost:
            if cost[item] > 0:
                budget = min(budget, num_items(item) // cost[item])
        for index in range(len(blocks)):
            share = (index + 1) * budget // len(blocks) - index * budget // len(blocks)
            payloads.append((blocks[index], target, share, level, variant))
    else:
        return False

    if num_items(output) >= target:
        return True
    start = get_time()
    ok = _dispatch(task, n, payloads)
    balance = num_items(output)
    quick_print("[RANK POLY FAST]", mode, "variant", variant, "workers", workers,
                "seconds", get_time() - start, "balance", balance, "target", target)
    return ok and balance >= target
