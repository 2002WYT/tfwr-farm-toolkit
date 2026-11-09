from farm_route import go, parallel


def _water(wanted, concurrent):
    level = get_water()
    if level < wanted:
        count = (wanted - level + 0.2499) // 0.25
        # Other drones may have checked the same stock. Reserve enough water for one full refill each.
        if count > 0 and num_items(Items.Water) >= count + 3 * (concurrent - 1):
            use_item(Items.Water, count)


def _distance(a, b, n):
    delta = abs(a - b)
    return min(delta, n - delta)


def _whole_square(x, y, n):
    if (x != 0 and x != n - 1) or (y != 0 and y != n - 1):
        return False
    # Check both wrapped neighbors at the corner to confirm that one pumpkin spans the field.
    value = measure()
    horizontal = East
    vertical = North
    if x == 0:
        horizontal = West
    if y == 0:
        vertical = South
    return value == measure(horizontal) and value == measure(vertical)


def _repair(n, points, target, variant, wanted, concurrent, whole=False):
    start = get_time()
    while len(points) > 0 and num_items(Items.Pumpkin) < target:
        remaining = []
        for x, y in points:
            if not go(x, y, n):
                return False
            if can_harvest():
                if whole and _whole_square(x, y, n):
                    return True
                continue
            if get_entity_type() == Entities.Dead_Pumpkin:
                if not plant(Entities.Pumpkin):
                    return False
                dose = wanted
                if variant >= 5 and not whole and num_items(Items.Water) >= concurrent * 5:
                    dose = 0.5
                _water(dose, concurrent)
            elif (variant >= 3 and get_time() - start >= 1.7
                  and num_items(Items.Fertilizer) >= concurrent):
                # Fertilize only the few plants that are holding up the block to limit yield loss from infection.
                use_item(Items.Fertilizer)
            if not can_harvest():
                remaining.append((x, y))
        points = remaining
        if get_time() - start > 30:
            return False
    return True


def _pumpkin_rows(n, bounds, target, variant):
    left, right, bottom, top = bounds
    first_x, first_y = left, bottom
    forward, back, vertical = East, West, North
    step_y = 1
    if variant >= 4 and n < 16:
        # Start each single-drone round at the corner closest to the previous finishing point.
        x, y = get_pos_x(), get_pos_y()
        if _distance(x, right - 1, n) < _distance(x, left, n):
            first_x = right - 1
            forward, back = West, East
        if _distance(y, top - 1, n) < _distance(y, bottom, n):
            first_y = top - 1
            step_y = -1
            vertical = South
    if not go(first_x, first_y, n):
        return False
    points = []
    concurrent = 1
    if n >= 16:
        concurrent = max_drones()
    wanted = 0.5
    if variant >= 3:
        wanted = 0.75
    if variant >= 5 and n == 6:
        wanted = 0.65
    height = top - bottom
    for row in range(height):
        y = first_y + row * step_y
        direct = forward
        if row % 2 == 1:
            direct = back
        for column in range(right - left):
            x = left + column
            if direct == West:
                x = right - 1 - column
            if get_ground_type() != Grounds.Soil:
                till()
            if not plant(Entities.Pumpkin):
                return False
            # Early plantings can mature during the first pass. When water is scarce, prioritize replacements.
            if (variant < 4 or (variant >= 5 and n == 6)
                    or (n < 16 and row >= height * 3 // 4)
                    or (n >= 16 and num_items(Items.Water) >= 8 * concurrent)):
                _water(wanted, concurrent)
            points.append((x, y))
            if column + 1 < right - left and not move(direct):
                return False
        if row + 1 < height and not move(vertical):
            return False

    return _repair(n, points, target, variant, wanted, concurrent, variant >= 5 and n == 6)


def _pumpkin_slice(n, x, y, side, begin, end, target):
    # Split the same serpentine path into two near-equal parts of 24 and 25 tiles.
    concurrent = max_drones()
    points = []
    for index in range(begin, end):
        row = index // side
        column = index % side
        tx = x + column
        direction = East
        if row % 2 == 1:
            tx = x + side - 1 - column
            direction = West
        ty = y + row
        if index == begin and not go(tx, ty, n):
            return False
        if get_ground_type() != Grounds.Soil:
            till()
        if not plant(Entities.Pumpkin):
            return False
        if num_items(Items.Water) >= concurrent * 8:
            _water(0.5, concurrent)
        points.append((tx, ty))
        if index + 1 < end:
            if column == side - 1:
                direction = North
            if not move(direction):
                return False
    return _repair(n, points, target, 5, 0.25, concurrent)


def _patch(n, x, y, side, target, variant, paired):
    # Each block can merge, harvest, and replant as soon as it is ready.
    # Public reference https://github.com/enihsyou/The-Farmer-Was-Replaced/blob/main/pumpkins.py
    while num_items(Items.Pumpkin) < target:
        child = None
        end = y + side
        if paired and variant >= 5:
            size = side * side
            mid = size // 2
            child = spawn_drone(_pumpkin_slice, n, x, y, side, mid, size, target)
            if child == None:
                mid = size
            ok = _pumpkin_slice(n, x, y, side, 0, mid, target)
        elif paired:
            middle = y + side // 2
            child = spawn_drone(_pumpkin_rows, n, (x, x + side, middle, end), target, variant)
            if child != None:
                end = middle
            ok = _pumpkin_rows(n, (x, x + side, y, end), target, variant)
        else:
            ok = _pumpkin_rows(n, (x, x + side, y, end), target, variant)
        if child != None:
            if variant >= 4 and ok and num_items(Items.Pumpkin) < target:
                # The main drone can move to the harvest tile while its helper is still replacing seedlings.
                ok = go(x, y, n)
            ok = wait_for(child) and ok
        if not ok:
            return False
        if num_items(Items.Pumpkin) >= target:
            return True
        if variant < 4 and not go(x, y, n):
            return False
        if not can_harvest() or not harvest():
            return False
    return True


def _patch_worker(worker, n, workers, config):
    side, stride, columns, target, variant, paired = config
    x = worker % columns * stride
    y = worker // columns * stride
    return _patch(n, x, y, side, target, variant, paired)


def rank_pumpkin(single, target, variant):
    n = get_world_size()
    if single and variant >= 5 and n > 6:
        # Public reference https://github.com/enihsyou/The-Farmer-Was-Replaced/blob/main/pumpkins_single.py
        set_world_size(6)
        n = get_world_size()
        if n != 6:
            variant = 4
    if single or n < 16:
        return _patch(n, 0, 0, n, target, variant, False)
    columns = n // 8
    patches = columns * columns
    if max_drones() < patches:
        return _patch(n, 0, 0, n, target, variant, False)
    paired = variant >= 3 and max_drones() >= 2 * patches
    outcomes = parallel(_patch_worker, n, patches, (7, 8, columns, target, variant, paired))
    for ok in outcomes:
        if not ok:
            return False
    return num_items(Items.Pumpkin) >= target
