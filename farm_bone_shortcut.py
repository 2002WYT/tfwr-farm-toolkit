from farm_bones import advance_shortcut, cycle_index


def _cell(index, n):
    width = n - 1
    if index == 0 or index > n * width:
        return 0, (n * n - index) % (n * n)
    y = (index - 1) // width
    x = index - y * width
    if y % 2 == 1:
        x = n - x
    return x, y


def _rows(plan, x, y, target_x, target_y):
    # North always advances the cycle within the serpentine rows. Use the last row that faces the needed direction.
    row = target_y
    if target_x > x and row % 2 == 1 or target_x < x and row % 2 == 0:
        row -= 1
    if row < y:
        return False
    plan.append((North, row - y))
    if target_x > x:
        plan.append((East, target_x - x))
    elif target_x < x:
        plan.append((West, x - target_x))
    plan.append((North, target_y - row))
    return True


def _west_edge(plan, x, y, minimum_row):
    # The west edge runs south. Join it at or above the target, using an odd row to travel west.
    entry = max(y, minimum_row)
    west_row = entry
    if x > 1 and entry % 2 == 0:
        if entry > y:
            west_row = entry - 1
        else:
            west_row = entry + 1
            entry += 1
    plan.append((North, west_row - y))
    plan.append((West, x - 1))
    plan.append((North, entry - west_row))
    plan.append((West, 1))
    return entry


def _route(index, cap, n):
    cells = n * n
    x, y = _cell(index, n)
    target_x, target_y = _cell(cap % cells, n)
    plan = []
    if target_x == 0:
        if cap > cells or index == 0:
            # The target is on the next circuit. Leave the current return edge and rejoin the next one from above.
            if x != 0:
                return None
            plan.append((East, 1))
            x = 1
        if x > 0:
            y = _west_edge(plan, x, y, target_y)
        if y < target_y:
            return None
        plan.append((South, y - target_y))
        return plan

    if cap > cells and x > 0:
        y = _west_edge(plan, x, y, y)
        x = 0
    if x == 0:
        exit_row = target_y
        if target_y % 2 == 1 and target_x > 1:
            # On an odd row, x=1 comes after the target. Approach from the even row below.
            exit_row -= 1
        exit_row = min(y, exit_row)
        plan.append((South, y - exit_row))
        plan.append((East, 1))
        x = 1
        y = exit_row
    if not _rows(plan, x, y, target_x, target_y):
        return None
    return plan


def _steps(plan):
    steps = 0
    for direction, count in plan:
        steps += count
    return steps


def fast_prefix(index, budget, n, directions, runs):
    if budget <= 0:
        return index, 0, True
    cells = n * n
    cap = index + budget
    plan = _route(index, cap, n)
    if cap > cells:
        x, y = _cell(index, n)
        if x > 0 and y > 0:
            # A southbound step can skip into the next circuit. Use it only if it stays before the target and shortens the route.
            below = cycle_index(x, y - 1, n)
            if cells + below <= cap:
                south_plan = _route(below, cap - cells, n)
                if south_plan != None and (plan == None or 1 + _steps(south_plan) < _steps(plan)):
                    plan = [(South, 1)]
                    for segment in south_plan:
                        plan.append(segment)
    if plan == None:
        return advance_shortcut(index, budget, n, directions, runs)

    # Advance in cycle order and use exactly the shortcut budget. The caller then follows the cycle for one tail length.
    moved = 0
    for direction, count in plan:
        for step in range(count):
            if not move(direction):
                return cycle_index(get_pos_x(), get_pos_y(), n), moved + step, False
        moved += count
    return cap % cells, moved, True
