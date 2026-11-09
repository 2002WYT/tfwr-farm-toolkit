from farm_route import go, parallel
from farm_cactus import sort_and_harvest
from farm_bones import run_bones
from farm_gold import run_gold
from farm_substance import run_substance


def run_supply(mode, windows):
    research = Unlocks.Watering
    item = Items.Water
    if mode == "fertilizer":
        research = Unlocks.Fertilizer
        item = Items.Fertilizer
    if num_unlocked(research) == 0:
        quick_print("[STOP]", "passive supply locked", item)
        return False

    start = get_time()
    water = num_items(Items.Water)
    fertilizer = num_items(Items.Fertilizer)
    for second in range(windows * 10):
        do_a_flip()
    elapsed = get_time() - start
    water_gain = num_items(Items.Water) - water
    fertilizer_gain = num_items(Items.Fertilizer) - fertilizer
    gain = water_gain
    if mode == "fertilizer":
        gain = fertilizer_gain
    quick_print("[SUPPLY]", "seconds", elapsed, "water", water_gain, "fertilizer", fertilizer_gain)
    quick_print("[RATE]", item, "net_per_min", gain * 60 / elapsed)
    return gain > 0


def collect_substance(rounds, workers, water_below):
    n = get_world_size()
    for batch in range(rounds):
        infection = "cross"
        if num_items(Items.Fertilizer) >= (n * n + 1) // 2:
            infection = "fertilizer"
        if not run_substance(1, workers, infection, water_below):
            return False
    return True


def inspect_worker(worker, n, workers, config):
    crop, trees = config
    first = worker * n // workers
    end = (worker + 1) * n // workers
    occupied = 0
    for y in range(first, end):
        for column in range(n):
            x = column
            if (y - first) % 2 == 1:
                x = n - 1 - column
            if not go(x, y, n):
                return [False, occupied]
            ground = get_ground_type()
            current = get_entity_type()
            if ground != Grounds.Grassland and ground != Grounds.Soil:
                return [False, occupied]
            if (current != None and current != Entities.Grass and current != Entities.Dead_Pumpkin
                    and current != crop and not (trees and current == Entities.Tree)):
                return [False, occupied + 1]
            if current == crop or (trees and current == Entities.Tree):
                occupied += 1
    return [True, occupied]


def sow(crop, water_below):
    if not plant(crop):
        return False
    if water_below > 0 and get_water() < water_below:
        use_item(Items.Water)
    return True


def field_worker(worker, n, workers, config):
    crop, water_below, trees, max_wait = config
    first = worker * n // workers
    end = (worker + 1) * n // workers
    planted = 0
    replanted = 0
    harvested = 0
    blocked = 0
    failed = 0
    pending = []
    flowers = []
    for y in range(first, end):
        for column in range(n):
            x = column
            if (y - first) % 2 == 1:
                x = n - 1 - column
            if not go(x, y, n):
                return [False, planted, replanted, harvested, blocked, failed, flowers]
            ground = get_ground_type()
            current = get_entity_type()
            if ground != Grounds.Soil and ground != Grounds.Grassland:
                blocked += 1
                continue
            if crop == Entities.Grass:
                if current == None or current == Entities.Grass or current == Entities.Dead_Pumpkin:
                    if ground == Grounds.Soil:
                        till()
                    if can_harvest():
                        if harvest():
                            harvested += 1
                        else:
                            failed += 1
                    else:
                        pending.append((x, y))
                else:
                    blocked += 1
                continue
            desired = crop
            if trees and (x + y) % 2 == 0:
                # Keep opposite edges apart on odd boards even when neighbors wrap.
                if n % 2 == 0 or n == 1 or (x < n - 1 and y < n - 1):
                    desired = Entities.Tree
            if current == crop or (trees and current == Entities.Tree):
                pending.append((x, y))
                continue
            if current != None and current != Entities.Grass and current != Entities.Dead_Pumpkin:
                blocked += 1
                continue
            if crop != Entities.Bush and ground == Grounds.Grassland:
                till()
            if sow(desired, water_below):
                planted += 1
                pending.append((x, y))
            else:
                failed += 1

    if blocked > 0 or failed > 0:
        return [False, planted, replanted, harvested, blocked, failed, flowers]

    deadline = get_time() + max_wait
    while len(pending) > 0 and get_time() < deadline:
        remaining = len(pending)
        next_pending = []
        for point in pending:
            x, y = point
            if not go(x, y, n):
                return [False, planted, replanted, harvested, blocked, failed, flowers]
            if can_harvest():
                if crop == Entities.Grass or crop == Entities.Bush or crop == Entities.Carrot:
                    if not harvest():
                        return [False, planted, replanted, harvested, blocked, failed, flowers]
                    harvested += 1
                elif crop == Entities.Sunflower:
                    flowers.append((x, y, measure()))
                # Ripe pumpkins and cacti stay in place for the global harvest.
            else:
                if crop == Entities.Pumpkin and get_entity_type() == Entities.Dead_Pumpkin:
                    if not sow(crop, water_below):
                        failed += 1
                        return [False, planted, replanted, harvested, blocked, failed, flowers]
                    replanted += 1
                next_pending.append(point)
        pending = next_pending
        # Limit the time since the last ripe tile, including on large single-drone stripes.
        if len(pending) < remaining:
            deadline = get_time() + max_wait
        elif len(pending) > 0:
            do_a_flip()
    return [len(pending) == 0, planted, replanted, harvested, blocked, failed, flowers]


def flower_worker(worker, n, workers, points):
    count = 0
    for point in points:
        x, y = point
        if go(x, y, n) and can_harvest() and harvest():
            count += 1
    return count


def harvest_flowers(stripes, n, workers):
    buckets = []
    for stripe in stripes:
        row = []
        for petals in range(9):
            row.append([])
        for flower in stripe[6]:
            x, y, petals = flower
            row[petals - 7].append((x, y))
        buckets.append(row)

    total = 0
    for petals in range(15, 6, -1):
        wave = []
        expected = 0
        for stripe in buckets:
            points = stripe[petals - 7]
            wave.append(points)
            expected += len(points)
        if expected == 0:
            continue
        count = 0
        for result in parallel(flower_worker, n, workers, wave, True):
            count += result
        quick_print("[FLOWER]", "petals", petals, "harvested", count, "expected", expected)
        if count != expected:
            return -1
        total += count
    return total


def run(mode, rounds, workers, water_below):
    if rounds < 1 or workers < 0 or water_below < 0 or water_below > 1:
        quick_print("[STOP]", "invalid configuration", mode, rounds, workers, water_below)
        return False
    if mode == "bone":
        return run_bones(rounds, True)
    if mode == "gold":
        return run_gold(rounds, workers)
    if mode == "substance":
        return collect_substance(rounds, workers, water_below)
    if mode == "water" or mode == "fertilizer":
        return run_supply(mode, rounds)
    crop = None
    output = None
    trees = False
    if mode == "hay":
        crop, output = Entities.Grass, Items.Hay
    elif mode == "wood":
        crop, output = Entities.Bush, Items.Wood
        trees = num_unlocked(Unlocks.Trees) > 0
    elif mode == "carrot":
        crop, output = Entities.Carrot, Items.Carrot
    elif mode == "pumpkin":
        crop, output = Entities.Pumpkin, Items.Pumpkin
    elif mode == "power":
        crop, output = Entities.Sunflower, Items.Power
    elif mode == "cactus":
        crop, output = Entities.Cactus, Items.Cactus
    if crop == None or num_unlocked(crop) == 0:
        quick_print("[STOP]", "unknown mode or crop locked", mode)
        return False

    n = get_world_size()
    if workers == 0 or workers > max_drones():
        workers = max_drones()
    if workers > n:
        workers = n
    if num_unlocked(Unlocks.Watering) == 0:
        water_below = 0
    # Snapshot the inventories around each joined batch. Power delta is net of use.
    items = [Items.Hay, Items.Wood, Items.Carrot, Items.Pumpkin, Items.Cactus, Items.Power, Items.Water]
    cost = {}
    if crop != Entities.Grass and crop != Entities.Bush:
        cost = get_cost(crop)
    quick_print("[FARM]", mode, "size", n, "workers", workers, "rounds", rounds, "water_below", water_below)
    for batch in range(1, rounds + 1):
        before = []
        for item in items:
            before.append(num_items(item))
        start_amount = num_items(output)
        start_time = get_time()
        start_ticks = get_tick_count()
        occupied = 0
        if batch == 1:
            for stripe in parallel(inspect_worker, n, workers, (crop, trees)):
                if not stripe[0]:
                    quick_print("[STOP]", "foreign crop, inaccessible tile or non-surface ground")
                    return False
                occupied += stripe[1]
        for item in cost:
            needed = cost[item] * (n * n - occupied)
            if num_items(item) < needed:
                quick_print("[STOP]", "seed budget", item, "have", num_items(item), "need", needed)
                return False
        planted = 0
        replanted = 0
        harvested = 0
        blocked = 0
        failed = 0
        pending_stripes = 0
        stripes = parallel(field_worker, n, workers, (crop, water_below, trees, 60))
        for stripe in stripes:
            if not stripe[0]:
                pending_stripes += 1
            planted += stripe[1]
            replanted += stripe[2]
            harvested += stripe[3]
            blocked += stripe[4]
            failed += stripe[5]
        ok = pending_stripes == 0
        if ok and crop == Entities.Pumpkin:
            ok = go(0, 0, n) and can_harvest() and harvest()
            if ok:
                harvested = 1
        elif ok and crop == Entities.Cactus:
            ok = sort_and_harvest(n, workers)
            if ok:
                harvested = 1
        elif ok and crop == Entities.Sunflower:
            harvested = harvest_flowers(stripes, n, workers)
            ok = harvested == n * n

        elapsed = get_time() - start_time
        ticks = get_tick_count() - start_ticks
        delta = num_items(output) - start_amount
        quick_print("[BATCH]", batch, "ok", ok, "planted", planted, "replanted", replanted,
                    "harvest_actions", harvested, "blocked", blocked, "plant_failures", failed,
                    "incomplete_stripes", pending_stripes)
        for index in range(len(items)):
            item = items[index]
            change = num_items(item) - before[index]
            if change != 0 or item == output:
                quick_print("[STOCK]", item, "delta", change, "balance", num_items(item))
        if elapsed > 0:
            quick_print("[RATE]", output, "net_per_min", delta * 60 / elapsed, "seconds", elapsed,
                        "main_ticks", ticks)
        if not ok:
            quick_print("[STOP]", "incomplete batch", batch)
            return False
    return True
