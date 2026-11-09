from farm_cactus import _sort_stripes, _sweep
from farm_route import go, move_axis, parallel


def _seed():
    if get_ground_type() != Grounds.Soil:
        till()
    return plant(Entities.Cactus)


def _move_distance(x, y, tx, ty, n):
    dx = abs(tx - x)
    dy = abs(ty - y)
    return min(dx, n - dx) + min(dy, n - dy)


def _insert(board, x, y, value):
    # Move the larger west or south neighbor into this tile to preserve the sorted boundary.
    board[(x, y)] = value
    while True:
        west = -1
        south = -1
        if x > 0:
            west = board[(x - 1, y)]
        if y > 0:
            south = board[(x, y - 1)]
        if max(west, south) <= value:
            return True
        if west >= south:
            tx, ty, side, previous = x - 1, y, West, west
        else:
            tx, ty, side, previous = x, y - 1, South, south
        if not swap(side):
            return False
        board[(x, y)] = previous
        board[(tx, ty)] = value
        if not ((tx > 0 and board[(tx - 1, ty)] > value)
                or (ty > 0 and board[(tx, ty - 1)] > value)):
            return True
        if not move(side):
            return False
        x, y = tx, ty


def _seed_and_insert(board, x, y, n):
    if not go(x, y, n) or not _seed():
        return False, 0
    seeded = get_time()
    return _insert(board, x, y, measure()), seeded


def _single(n, diagonal):
    # Public reference https://github.com/enihsyou/The-Farmer-Was-Replaced/blob/main/cactus_single.py
    board = {}
    latest = 0
    lines = n
    if diagonal:
        lines = n * 2 - 1
    for line in range(lines):
        points = []
        if diagonal:
            for x in range(max(0, line - n + 1), min(n, line + 1)):
                points.append((x, line - x))
        else:
            for x in range(n):
                points.append((x, line))
        while len(points) > 0:
            index = 0
            if diagonal:
                cx = get_pos_x()
                cy = get_pos_y()
                distance = n * 2
                for i in range(len(points)):
                    x, y = points[i]
                    candidate = _move_distance(cx, cy, x, y, n)
                    if candidate < distance:
                        distance = candidate
                        index = i
            x, y = points.pop(index)
            ok, latest = _seed_and_insert(board, x, y, n)
            if not ok:
                return False, latest
    return True, latest


def _row_sort(y, n):
    # The drone is already at the east end of the row and can start the reverse pass.
    low = 0
    high = n - 1
    while low < high:
        low = _sweep(high, low, -1, West, East)
        if low == None:
            return False
        if low == high:
            break
        if not go(low, y, n):
            return False
        high = _sweep(low, high, 1, East, West)
        if high == None:
            return False
        if low < high and not go(high, y, n):
            return False
    return True


def _cached_sweep(values, start, end, step, forward, backward, cursor, n):
    advance, retreat = forward, backward
    if step < 0:
        advance, retreat = backward, forward
    last = start
    for position in range(start, end, step):
        next_position = position + step
        previous = position - step
        value = values[position] * step
        ahead = values[next_position] * step
        behind = value
        if position != start:
            behind = values[previous] * step
        while True:
            if value > ahead:
                neighbor = next_position
                direction = advance
                ahead = value
                last = position
            elif position != start and behind > value:
                neighbor = previous
                direction = retreat
                behind = value
                if last != position:
                    last = previous
            else:
                break
            # Find the inversion in the cache before moving. Skip scans and turns on sorted stretches.
            offset = position - cursor
            if offset == 1:
                if not move(forward):
                    return None, cursor
            elif offset == -1:
                if not move(backward):
                    return None, cursor
            elif offset != 0:
                if not move_axis(offset, forward, backward, n):
                    return None, cursor
            cursor = position
            if not swap(direction):
                return None, cursor
            old_value = values[position]
            values[position] = values[neighbor]
            values[neighbor] = old_value
            value = values[position] * step
    return last, cursor


def _cached_sort(values, high, forward, backward, cursor, n):
    low = 0
    # Planting or reading completed the forward pass. Start with the reverse pass.
    while low < high:
        low, cursor = _cached_sweep(values, high, low, -1, forward, backward, cursor, n)
        if low == None:
            return False
        if low < high:
            high, cursor = _cached_sweep(values, low, high, 1, forward, backward, cursor, n)
            if high == None:
                return False
    return True


def _capture_column(x, n):
    if not go(x, 0, n):
        return False
    if n == 1:
        return True
    # Measure sizes during the forward pass, then use the cache for later passes.
    value = measure()
    behind = value
    values = []
    last = 0
    for y in range(n - 1):
        ahead = measure(North)
        while True:
            if value > ahead:
                if not swap(North):
                    return False
                value, ahead = ahead, value
                last = y
            elif y > 0 and behind > value:
                if not swap(South):
                    return False
                value, behind = behind, value
                values[y - 1] = behind
                if last != y:
                    last = y - 1
            else:
                break
        values.append(value)
        if y + 1 < n - 1 and not move(North):
            return False
        behind = value
        value = ahead
    values.append(value)
    return _cached_sort(values, last, North, South, n - 2, n)


def _seed_rows(worker, n, workers, preswap, cached=False):
    # Let one drone plant and sort the same row to save a synchronization step.
    # Public reference https://github.com/enihsyou/The-Farmer-Was-Replaced/blob/main/cactus.py
    latest = 0
    for y in range(worker, n, workers):
        if not go(0, y, n):
            return False, latest
        values = []
        last = 0
        for x in range(n):
            if not _seed():
                return False, latest
            latest = get_time()
            if cached:
                value = measure()
                if x > 0 and value < values[x - 1]:
                    if not swap(West):
                        return False, latest
                    values[x - 1], value = value, values[x - 1]
                    last = x - 1
                values.append(value)
            elif preswap and x > 0 and measure() < measure(West):
                if not swap(West):
                    return False, latest
            if x < n - 1 and not move(East):
                return False, latest
        if cached:
            if not _cached_sort(values, last, East, West, n - 1, n):
                return False, latest
        elif not _row_sort(y, n):
            return False, latest
    return True, latest


def _fork_stripes(n, workers, start, end, columns, cached):
    if end - start == 1:
        if columns:
            if not cached:
                return _sort_stripes(start, n, workers, True), 0
            for x in range(start, n, workers):
                if not _capture_column(x, n):
                    return False, 0
            return True, 0
        return _seed_rows(start, n, workers, True, cached)
    # Launch drones in a tree so startup depends on its depth.
    mid = (start + end) // 2
    child = spawn_drone(_fork_stripes, n, workers, mid, end, columns, cached)
    left_ok, left_time = _fork_stripes(n, workers, start, mid, columns, cached)
    if child == None:
        right_ok, right_time = _fork_stripes(n, workers, mid, end, columns, cached)
    else:
        right_ok, right_time = wait_for(child)
    return left_ok and right_ok, max(left_time, right_time)


def rank_cactus(single, target, variant):
    n = get_world_size()
    workers = min(n, max_drones())
    while num_items(Items.Cactus) < target:
        before = num_items(Items.Cactus)
        cost = get_cost(Entities.Cactus)
        for item in cost:
            if num_items(item) < cost[item] * n * n:
                return False
        latest = 0
        if single or workers == 1:
            ok, latest = _single(n, variant == 3)
            if not ok:
                return False
        elif variant >= 3:
            ok, latest = _fork_stripes(n, workers, 0, workers, False, variant >= 4)
            if not ok:
                return False
            ok, unused = _fork_stripes(n, workers, 0, workers, True, variant >= 4)
            if not ok:
                return False
        else:
            for ok, seeded in parallel(_seed_rows, n, workers, False):
                if not ok:
                    return False
                latest = max(latest, seeded)
            for ok in parallel(_sort_stripes, n, workers, True):
                if not ok:
                    return False
        # Cacti take one second to grow without random variation. Moving and swapping preserve growth progress.
        while get_time() - latest < 1.05:
            pass
        if not harvest() or num_items(Items.Cactus) <= before:
            return False
    return True
