from farm_route import go, parallel


def _bounds(worker, n, workers):
    if n == 32 and workers == 32:
        left = worker % 8 * 4
        bottom = worker // 8 * 8
        return left, left + 4, bottom, bottom + 8
    return 0, n, worker * n // workers, (worker + 1) * n // workers


def _wait_mature(deadline):
    if not can_harvest() and get_water() < 0.7:
        tanks = (0.9499 - get_water()) // 0.25
        if tanks > 0 and num_items(Items.Water) >= tanks + 3 * (max_drones() - 1):
            use_item(Items.Water, tanks)
    while not can_harvest():
        if get_time() >= deadline:
            return False
    return True


def _seed_block(worker, n, workers, signal):
    left, right, bottom, top = _bounds(worker, n, workers)
    mark_x = (left + right) // 2
    mark_y = (bottom + top) // 2
    buckets = [[], [], [], [], [], [], [], [], []]
    if not go(left, bottom, n):
        return False, buckets, (mark_x, mark_y)
    for y in range(bottom, top):
        side = East
        if (y - bottom) % 2 == 1:
            side = West
        for column in range(right - left):
            x = left + column
            if side == West:
                x = right - 1 - column
            if not (signal and x == mark_x and y == mark_y):
                if get_ground_type() != Grounds.Soil:
                    till()
                if get_entity_type() != Entities.Sunflower and not plant(Entities.Sunflower):
                    return False, buckets, (mark_x, mark_y)
                petals = measure()
                buckets[petals - 7].append((x, y))
                # Harvest high-petal flowers first and water only the later high-petal plantings.
                if petals >= 13 and y >= (bottom + top) // 2 and get_water() < 0.45:
                    if num_items(Items.Water) >= 2 + 3 * (workers - 1):
                        use_item(Items.Water, 2)
            if column + 1 < right - left and not move(side):
                return False, buckets, (mark_x, mark_y)
        if y + 1 < top and not move(North):
            return False, buckets, (mark_x, mark_y)
    return True, buckets, (mark_x, mark_y)


def _nearest(points, n):
    x = get_pos_x()
    y = get_pos_y()
    best = 0
    score = n * 2
    for index in range(len(points)):
        tx, ty = points[index]
        dx = abs(tx - x)
        dy = abs(ty - y)
        distance = min(dx, n - dx) + min(dy, n - dy)
        if distance < score:
            score = distance
            best = index
    return points.pop(best)


def _cut_points(points, limit, n):
    harvested = 0
    deadline = get_time() + 30
    for index in range(limit):
        x, y = _nearest(points, n)
        if not go(x, y, n) or not _wait_mature(deadline) or not harvest():
            return -1
        harvested += 1
    return harvested


def _cut_worker(worker, n, workers, points):
    return _cut_points(points, len(points), n)


def _wave_batch(n, workers, keep):
    records = parallel(_seed_block, n, workers, False)
    for ok, buckets, marker in records:
        if not ok:
            return False
    remaining = n * n - keep
    for petals in range(8, -1, -1):
        if remaining == 0:
            break
        if workers == 1:
            points = records[0][1][petals]
            expected = min(remaining, len(points))
            if _cut_points(points, expected, n) != expected:
                return False
            remaining -= expected
        else:
            wave = []
            expected = 0
            for ok, buckets, marker in records:
                points = buckets[petals]
                wave.append(points)
                expected += len(points)
            if expected > 0:
                done = 0
                for count in parallel(_cut_worker, n, workers, wave, True):
                    if count < 0:
                        return False
                    done += count
                if done != expected:
                    return False
                remaining -= done
    return remaining == 0


def _signal(mark, at_flower, n, deadline):
    # Use harvested hay to signal completion. After harvesting a flower, plant grass in place to save a trip.
    if at_flower:
        if not plant(Entities.Grass):
            return False
    else:
        x, y = mark
        if not go(x, y, n):
            return False
    return _wait_mature(deadline) and harvest()


def _sync_worker(worker, n, workers, config):
    carrots_done, hay_start, signal_gain, deadline = config
    ok, buckets, marker = _seed_block(worker, n, workers, True)
    if not ok:
        return False
    while num_items(Items.Carrot) > carrots_done:
        if get_time() >= deadline:
            return False
    for petals in range(8, -1, -1):
        points = buckets[petals]
        count = len(points)
        if _cut_points(points, count, n) != count:
            return False
        if petals == 0:
            break
        if not _signal(marker, count > 0, n, deadline):
            return False
        # Wait for every drone to finish the current petal group before moving on to preserve the bonus.
        barrier = hay_start + (8 - petals + 1) * workers * signal_gain
        while num_items(Items.Hay) < barrier:
            if get_time() >= deadline:
                return False
    return True


def _sync_batch(n, workers, carrot_cost):
    # Public reference https://github.com/enihsyou/The-Farmer-Was-Replaced/blob/main/sunflowers.py
    expected_cost = carrot_cost * (n * n - workers)
    carrots = num_items(Items.Carrot)
    if carrots < expected_cost:
        return False
    hay_start = num_items(Items.Hay)
    signal_gain = 2 ** (num_unlocked(Unlocks.Grass) - 1)
    deadline = get_time() + 60
    args = (carrots - expected_cost, hay_start, signal_gain, deadline)
    for ok in parallel(_sync_worker, n, workers, args):
        if not ok:
            return False
    return True


def rank_power(single, target, variant):
    n = get_world_size()
    workers = 1
    if not single:
        workers = min(n, max_drones())
    carrot_cost = get_cost(Entities.Sunflower)[Items.Carrot]
    while num_items(Items.Power) < target:
        before = num_items(Items.Power)
        if variant >= 3 and workers > 1:
            if not _sync_batch(n, workers, carrot_cost):
                return False
        else:
            keep = 0
            if workers == 1 and variant >= 3 and n * n > 9:
                keep = 9
            if not _wave_batch(n, workers, keep):
                return False
        if num_items(Items.Power) <= before:
            return False
    return True
