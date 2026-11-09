from farm_route import go
from farm_rank_poly import _blocks, _cycle, _dispatch, _install


def _pattern(variant):
    # 让主作物靠近 4×8 分区中部，保留能接收伴生请求的边缘地块。
    if variant == 2:
        return [(0, 3), (1, 2), (1, 4), (1, 6), (2, 1), (2, 5), (2, 6), (3, 2)]
    return [(0, 4), (1, 1), (1, 2), (1, 5), (2, 1), (2, 2), (2, 5), (2, 6)]


def _sow(helpers, claims, seeds, level):
    for attempt in range(24):
        if not plant(Entities.Carrot):
            return [False, seeds, -2]
        seeds -= 1
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
        if helper >= 0 or seeds == 0 or attempt == 23:
            # 整次补水只调用一次；短缺时留一个小余量，避免其他无人机同时用完库存。
            water = get_water()
            if water < level:
                doses = -((water - level) * 4 // 1)
                if num_items(Items.Water) > doses + 4:
                    use_item(Items.Water, doses)
            return [True, seeds, helper]
        # 只清掉自己刚种下且伴生位置不合适的幼苗。
        if not harvest():
            return [False, seeds, -2]
    return [False, seeds, -2]


def _work(worker, n, workers, config):
    bounds, target, seeds, variant = config
    x0, x1, y0, y1 = bounds
    if num_items(Items.Carrot) >= target:
        return True
    if not go(x0, y0, n):
        return False

    pattern = _pattern(variant)
    path = []
    helpers = {}
    claims = []
    installed = []
    requests = []
    grassland = []
    for point, direction in _cycle(bounds):
        x, y = point
        crop = get_entity_type()
        ground = get_ground_type()
        if (ground != Grounds.Grassland and ground != Grounds.Soil) or (crop != None and crop != Entities.Grass):
            return False
        source = (x - x0, y - y0) in pattern
        index = len(path)
        if not source:
            helpers[point] = index
        path.append((index, direction, source))
        claims.append([None, 0])
        installed.append(crop)
        requests.append(-2)
        grassland.append(ground == Grounds.Grassland)
        if not move(direction):
            return False

    level = 0.68
    if variant == 2:
        level = 0.84
    active = 0
    deadline = get_time() + 3600
    while num_items(Items.Carrot) < target and get_time() < deadline:
        for index, direction, source in path:
            if source:
                helper = requests[index]
                sow = helper == -2
                if not sow and can_harvest():
                    if helper == -1 or installed[helper] == claims[helper][0]:
                        if not harvest():
                            return False
                        if num_items(Items.Carrot) >= target:
                            return True
                        if helper >= 0:
                            claims[helper][1] -= 1
                        requests[index] = -2
                        active -= 1
                        sow = True
                if sow and seeds > 0:
                    if grassland[index]:
                        till()
                        grassland[index] = False
                    ok, seeds, helper = _sow(helpers, claims, seeds, level)
                    if not ok:
                        return False
                    requests[index] = helper
                    active += 1
                elif sow and active == 0:
                    # 本机没有种子和待收作物，其他分区仍可继续。
                    return True
            else:
                crop, count = claims[index]
                if count > 0 and installed[index] != crop:
                    if not _install(crop):
                        return False
                    installed[index] = crop
            if not move(direction):
                return False
    return num_items(Items.Carrot) >= target


def run_rank_poly_carrot(target, variant=1):
    if get_world_size() != 32 or max_drones() < 32 or target <= 0 or (variant != 1 and variant != 2):
        return False
    if num_items(Items.Carrot) >= target:
        return True
    budget = 1000000000
    cost = get_cost(Entities.Carrot)
    for item in cost:
        if cost[item] > 0:
            budget = min(budget, num_items(item) // cost[item])
    blocks = _blocks(32, False, 32)
    payloads = []
    for index in range(32):
        seeds = (index + 1) * budget // 32 - index * budget // 32
        payloads.append((blocks[index], target, seeds, variant))
    start = get_time()
    ok = _dispatch(_work, 32, payloads)
    balance = num_items(Items.Carrot)
    quick_print("[RANK CARROT]", "variant", variant, "seconds", get_time() - start,
                "balance", balance, "target", target)
    return ok and balance >= target
