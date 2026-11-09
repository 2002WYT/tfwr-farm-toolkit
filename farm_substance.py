from farm_route import go, parallel


def _is_tree(x, y, n):
    # Leave the last row and column open on odd farms to separate wrapped trees.
    return (x + y) % 2 == 0 and (n == 1 or n % 2 == 0 or (x < n - 1 and y < n - 1))


def _is_cross(x, y, n):
    # These centers have disjoint sets of orthogonal neighbors. Infection does not wrap.
    return (0 <= x < n and 0 <= y < n and x % 2 == 0 and y % 2 == 1
            and (x // 2 + y // 2) % 2 == 0)


def _covered_by_cross(x, y, n):
    if x % 2 == 0:
        return _is_cross(x, y - 1, n) or _is_cross(x, y + 1, n)
    return _is_cross(x - 1, y, n) or _is_cross(x + 1, y, n)


def _inspect(worker, n, workers, cross):
    trees = 0
    doses = 0
    centers = 0
    for y in range(worker * n // workers, (worker + 1) * n // workers):
        for x in range(n):
            if not go(x, y, n):
                return [False, 0, 0, 0]
            ground = get_ground_type()
            crop = get_entity_type()
            if (ground != Grounds.Grassland and ground != Grounds.Soil) or (crop != None and crop != Entities.Grass):
                return [False, 0, 0, 0]
            if _is_tree(x, y, n):
                trees += 1
                if not cross or not _covered_by_cross(x, y, n):
                    doses += 1
            elif cross and _is_cross(x, y, n):
                centers += 1
    return [True, trees, doses, centers]


def _sow_trees(worker, n, workers, config):
    cross, water_below, companion_unlocked = config
    requests = []
    for y in range(worker * n // workers, (worker + 1) * n // workers):
        for x in range(y % 2, n, 2):
            if not _is_tree(x, y, n):
                continue
            if not go(x, y, n) or not plant(Entities.Tree):
                return [False, requests]
            if water_below > 0 and get_water() < water_below and num_items(Items.Water) > 0:
                use_item(Items.Water)
            if not cross or not _covered_by_cross(x, y, n):
                if not use_item(Items.Fertilizer):
                    return [False, requests]
            if companion_unlocked:
                request = get_companion()
                if request != None:
                    requests.append(request)
    return [True, requests]


def _choose_companions(stripes, n, cross):
    votes = {}
    for stripe in stripes:
        for crop, point in stripe[1]:
            x, y = point
            if _is_tree(x, y, n) or (cross and _is_cross(x, y, n) and crop != Entities.Grass):
                continue
            if point not in votes:
                votes[point] = {}
            counts = votes[point]
            if crop not in counts:
                counts[crop] = 0
            counts[crop] += 1

    choices = [Entities.Grass, Entities.Bush]
    carrot_budget = 0
    if num_unlocked(Unlocks.Carrots) > 0:
        choices.append(Entities.Carrot)
        carrot_budget = n * n
        cost = get_cost(Entities.Carrot)
        for item in cost:
            carrot_budget = min(carrot_budget, num_items(item) // cost[item])

    plan = {}
    boosted = 0
    for point in votes:
        counts = votes[point]
        choice = None
        most = 0
        for crop in choices:
            if crop not in counts or (crop == Entities.Carrot and carrot_budget == 0):
                continue
            count = counts[crop]
            if count > most:
                choice = crop
                most = count
        if choice != None:
            plan[point] = choice
            boosted += most
            if choice == Entities.Carrot:
                carrot_budget -= 1
    return [plan, boosted]


def _set_companions(worker, n, workers, config):
    cross, plan = config
    planted = []
    for y in range(worker * n // workers, (worker + 1) * n // workers):
        for x in range(n):
            center = cross and _is_cross(x, y, n)
            point = (x, y)
            if center:
                crop = Entities.Grass
            elif point in plan:
                crop = plan[point]
            else:
                continue
            if not go(x, y, n):
                return [False, planted]
            if get_entity_type() != crop:
                restore = crop == Entities.Carrot and get_ground_type() == Grounds.Grassland
                if restore:
                    till()
                if not plant(crop):
                    if restore:
                        till()
                    return [False, planted]
                if crop != Entities.Grass:
                    planted.append((x, y, crop, restore))
            if center and not use_item(Items.Weird_Substance):
                return [False, planted]
    return [True, planted]


def _harvest_ripe(crop):
    if get_entity_type() != crop:
        return False
    deadline = get_time() + 30
    while not can_harvest():
        if get_time() >= deadline:
            return False
        do_a_flip()
    return harvest()


def _harvest_trees(worker, n, workers, unused):
    count = 0
    for y in range(worker * n // workers, (worker + 1) * n // workers):
        for x in range(y % 2, n, 2):
            if not _is_tree(x, y, n):
                continue
            if not go(x, y, n) or not _harvest_ripe(Entities.Tree):
                return count
            count += 1
    return count


def _clean_companions(worker, n, workers, planted):
    ok = True
    for x, y, crop, restore in planted:
        if go(x, y, n) and _harvest_ripe(crop):
            if restore:
                till()
        else:
            ok = False
    return ok


def run_substance(rounds, workers, infection="fertilizer", water_below=0.1):
    if rounds < 1 or workers < 0 or water_below < 0 or water_below > 1:
        quick_print("[STOP]", "invalid substance configuration")
        return False
    if infection != "fertilizer" and infection != "cross":
        quick_print("[STOP]", "unknown substance infection method", infection)
        return False
    if num_unlocked(Unlocks.Trees) == 0 or num_unlocked(Unlocks.Fertilizer) == 0:
        quick_print("[STOP]", "substance requires trees and fertilizer")
        return False
    if num_unlocked(Unlocks.Watering) == 0:
        water_below = 0

    n = get_world_size()
    if workers == 0:
        workers = max_drones()
    workers = min(workers, max_drones(), n)
    cross = infection == "cross"
    companions = num_unlocked(Unlocks.Polyculture) > 0
    quick_print("[FARM]", "substance", "size", n, "workers", workers, "rounds", rounds,
                "infection", infection, "water_below", water_below)

    for batch in range(1, rounds + 1):
        before = num_items(Items.Weird_Substance)
        fertilizer = num_items(Items.Fertilizer)
        water = num_items(Items.Water)
        started = get_time()
        trees = 0
        doses = 0
        centers = 0
        for ok, count, needed, casts in parallel(_inspect, n, workers, cross):
            if not ok:
                quick_print("[STOP]", "foreign crop, inaccessible tile or non-surface ground")
                return False
            trees += count
            doses += needed
            centers += casts
        if num_items(Items.Fertilizer) < doses or num_items(Items.Weird_Substance) < centers:
            quick_print("[STOP]", "infection budget", "fertilizer_needed", doses, "substance_needed", centers)
            return False

        stripes = parallel(_sow_trees, n, workers, (cross, water_below, companions))
        for stripe in stripes:
            if not stripe[0]:
                quick_print("[STOP]", "could not plant or infect all substance trees")
                return False
        plan, boosted = _choose_companions(stripes, n, cross)
        ready = True
        cleanup = []
        for ok, planted in parallel(_set_companions, n, workers, (cross, plan)):
            ready = ready and ok
            cleanup.append(planted)

        harvested = 0
        if ready:
            for count in parallel(_harvest_trees, n, workers, None):
                harvested += count
        cleaned = True
        for ok in parallel(_clean_companions, n, workers, cleanup, True):
            cleaned = cleaned and ok

        elapsed = get_time() - started
        balance = num_items(Items.Weird_Substance)
        delta = balance - before
        ok = ready and cleaned and harvested == trees and delta > 0
        quick_print("[BATCH]", batch, "ok", ok, "trees", trees, "boosted", boosted, "harvest_actions", harvested,
                    "fertilizer_doses", doses, "substance_casts", centers,
                    "net_fertilizer_used", fertilizer - num_items(Items.Fertilizer),
                    "net_water_used", water - num_items(Items.Water))
        quick_print("[STOCK]", Items.Weird_Substance, "delta", delta, "balance", balance)
        quick_print("[RATE]", Items.Weird_Substance, "net_per_min", delta * 60 / elapsed, "seconds", elapsed)
        if not ok:
            quick_print("[STOP]", "incomplete substance batch", batch)
            return False
    return True
