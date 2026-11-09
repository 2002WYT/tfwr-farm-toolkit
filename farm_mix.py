from farm_route import go, parallel


def _regions(n, workers):
    # Use compact rectangular blocks so one drone can manage nearby crops and companions.
    rows = 1
    while (rows + 1) ** 2 <= workers:
        rows += 1
    regions = []
    for row in range(rows):
        cols = (row + 1) * workers // rows - row * workers // rows
        for col in range(cols):
            regions.append((col * n // cols, (col + 1) * n // cols,
                            row * n // rows, (row + 1) * n // rows))
    return regions


def _inspect(n, bounds, crop):
    x0, x1, y0, y1 = bounds
    sources = []
    helpers = {}
    order = []
    for y in range(y0, y1):
        direction = East
        first = x0
        step = 1
        if (y - y0) % 2 == 1:
            direction = West
            first = x1 - 1
            step = -1
        if not go(first, y, n):
            return [False, sources, helpers, order]
        for offset in range(x1 - x0):
            if offset > 0 and not move(direction):
                return [False, sources, helpers, order]
            x = first + offset * step
            ground = get_ground_type()
            current = get_entity_type()
            if ground != Grounds.Grassland and ground != Grounds.Soil:
                return [False, sources, helpers, order]
            point = (x, y)
            protected = current != None and (current != Entities.Grass or ground == Grounds.Soil)
            main = (x + y) % 2 == 0
            if crop == Entities.Tree and n > 1 and n % 2 == 1 and (x == n - 1 or y == n - 1):
                # Leave the outer edge of odd-sized fields clear to keep trees apart across the wrap.
                main = False
            if main and not protected:
                sources.append(point)
            else:
                # Existing crops can supply a bonus. Only replace companions planted by this script.
                helpers[point] = [current, ground, protected, False]
                order.append(point)
    return [True, sources, helpers, order]


def _prepare(n, crop, sources, helpers, water_below, mixed):
    votes = {}
    planted = []
    for point in sources:
        x, y = point
        if not go(x, y, n):
            break
        if crop == Entities.Grass:
            if get_entity_type() != Entities.Grass and get_ground_type() == Grounds.Soil:
                till()
        else:
            tilled = crop == Entities.Carrot and get_ground_type() == Grounds.Grassland
            if tilled:
                till()
            if not plant(crop):
                if tilled:
                    till()
                break
        planted.append(point)
        if water_below > 0 and get_water() < water_below and num_items(Items.Water) > 0:
            use_item(Items.Water)
        if mixed:
            request = get_companion()
            if request != None:
                kind, position = request
                if position in helpers:
                    if position not in votes:
                        votes[position] = {}
                    counts = votes[position]
                    if kind not in counts:
                        counts[kind] = 0
                    counts[kind] += 1
    return [planted, votes]


def _wait_harvest(crop):
    if get_entity_type() != crop:
        return False
    # Existing trees can multiply the growth time of adjacent trees.
    deadline = get_time() + 180
    while not can_harvest():
        if get_time() >= deadline:
            return False
        do_a_flip()
    return harvest()


def _apply_helpers(n, votes, order, helpers, choices, carrot_budget):
    boosted = 0
    for point in order:
        if point not in votes:
            continue
        state = helpers[point]
        current, ground, protected, owned = state
        counts = votes[point]
        choice = current
        best = 0
        if current in counts:
            best = counts[current]
        if not protected:
            # Keep the current crop on a tie to save replanting work and materials.
            for kind in choices:
                if kind in counts and counts[kind] > best:
                    if kind != Entities.Carrot or carrot_budget > 0:
                        choice = kind
                        best = counts[kind]
        if choice == current:
            boosted += best
            continue
        x, y = point
        if not go(x, y, n):
            return [False, boosted, carrot_budget]
        if owned:
            if not can_harvest():
                if current in counts:
                    boosted += counts[current]
                continue
            if get_entity_type() != current or not harvest():
                return [False, boosted, carrot_budget]
            state[0] = get_entity_type()
            state[3] = False

        tilled = choice == Entities.Carrot and get_ground_type() == Grounds.Grassland
        if tilled:
            till()
        if get_entity_type() != choice:
            if not plant(choice):
                if tilled:
                    till()
                return [False, boosted, carrot_budget]
            state[3] = True
            if choice == Entities.Carrot:
                carrot_budget -= 1
        state[0] = choice
        boosted += best
    return [True, boosted, carrot_budget]


def _collect(n, crop, pending):
    harvested = 0
    deadline = get_time() + 180
    # Harvest ripe tiles first. Wait for growth only after a pass with no progress.
    while len(pending) > 0 and get_time() < deadline:
        waiting = []
        for point in pending:
            x, y = point
            if not go(x, y, n) or get_entity_type() != crop:
                return [False, harvested]
            if can_harvest():
                if not harvest():
                    return [False, harvested]
                harvested += 1
            else:
                waiting.append(point)
        if len(waiting) == len(pending):
            do_a_flip()
        else:
            deadline = get_time() + 180
        pending = waiting
    return [len(pending) == 0, harvested]


def _cleanup(n, helpers, order):
    ok = True
    for point in order:
        crop, ground, protected, owned = helpers[point]
        if not owned:
            continue
        x, y = point
        if go(x, y, n) and _wait_harvest(crop):
            if get_ground_type() != ground:
                till()
        else:
            ok = False
    return ok


def _work(worker, n, workers, config):
    bounds, crop, output, rounds, target, water_below, choices, budget, mixed = config
    ok, sources, helpers, order = _inspect(n, bounds, crop)
    if not ok or len(sources) == 0:
        return [ok, 0, 0, 0]

    batches = 0
    harvested = 0
    boosted = 0
    while (target > 0 and num_items(output) < target) or (target == 0 and batches < rounds):
        helper_budget = budget
        if crop == Entities.Carrot:
            # Give each drone its own seed budget and reserve seeds for the primary crop.
            if budget < len(sources):
                ok = target > 0
                break
            budget -= len(sources)
            helper_budget = 0
        planted, votes = _prepare(n, crop, sources, helpers, water_below, mixed)
        prepared = len(planted) == len(sources)
        if prepared:
            prepared, added, helper_budget = _apply_helpers(n, votes, order, helpers, choices, helper_budget)
            boosted += added
        if crop != Entities.Carrot:
            budget = helper_budget
        collected, count = _collect(n, crop, planted)
        harvested += count
        if not prepared or not collected:
            ok = False
            break
        batches += 1
    cleaned = _cleanup(n, helpers, order)
    return [ok and cleaned, batches, harvested, boosted]


def run_mix(mode, rounds, workers, water_below, target=0):
    if (target == 0 and rounds < 1) or workers < 0 or water_below < 0 or water_below > 1 or target < 0:
        quick_print("[STOP]", "invalid mixed-crop configuration", mode)
        return False
    if mode == "hay":
        crop, output = Entities.Grass, Items.Hay
    elif mode == "wood":
        crop, output = Entities.Bush, Items.Wood
        if num_unlocked(Unlocks.Trees) > 0:
            crop = Entities.Tree
    elif mode == "carrot":
        crop, output = Entities.Carrot, Items.Carrot
    else:
        quick_print("[STOP]", "unknown mixed-crop mode", mode)
        return False
    if num_unlocked(crop) == 0:
        quick_print("[STOP]", "mixed crop locked", crop)
        return False
    before = num_items(output)
    if target > 0 and before >= target:
        return True
    if num_unlocked(Unlocks.Watering) == 0:
        water_below = 0
    mixed = num_unlocked(Unlocks.Polyculture) > 0
    choices = [Entities.Grass, Entities.Bush]
    if num_unlocked(Unlocks.Trees) > 0:
        choices.append(Entities.Tree)
    budget = 0
    if num_unlocked(Unlocks.Carrots) > 0:
        choices.append(Entities.Carrot)
        cost = get_cost(Entities.Carrot)
        budget = 1000000000
        for item in cost:
            if cost[item] > 0:
                budget = min(budget, num_items(item) // cost[item])

    n = get_world_size()
    if workers == 0:
        workers = max_drones()
    workers = min(workers, n, max_drones())
    payloads = []
    previous = 0
    area = 0
    for bounds in _regions(n, workers):
        x0, x1, y0, y1 = bounds
        area += (x1 - x0) * (y1 - y0)
        allocated = budget * area // (n * n)
        payloads.append((bounds, crop, output, rounds, target, water_below, choices, allocated - previous, mixed))
        previous = allocated

    quick_print("[FARM]", mode, "mixed", mixed, "size", n, "workers", workers, "rounds", rounds, "target", target)
    started = get_time()
    done = True
    batches = 0
    harvested = 0
    boosted = 0
    for ok, count, collected, matches in parallel(_work, n, workers, payloads, True):
        done = done and ok
        batches = max(batches, count)
        harvested += collected
        boosted += matches
    elapsed = get_time() - started
    balance = num_items(output)
    delta = balance - before
    done = done and delta > 0 and (target == 0 or balance >= target)
    quick_print("[MIX]", mode, "ok", done, "batches", batches, "harvest_actions", harvested, "boosted", boosted)
    quick_print("[STOCK]", output, "delta", delta, "balance", balance)
    if elapsed > 0:
        quick_print("[RATE]", output, "net_per_min", delta * 60 / elapsed, "seconds", elapsed)
    return done
