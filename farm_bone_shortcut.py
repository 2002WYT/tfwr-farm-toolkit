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
    # 蛇形区向北总是前进。横向移动选最后一条方向一致的行。
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
    # 西侧返程从上向下。入口行必须不低于目标，奇数行才可向西横穿。
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
            # 已绕回下一圈。先离开当前返程，再从上方接入下一圈返程。
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
            # 奇数行的 x=1 在目标之后，应从下面的偶数行进入。
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
            # 向南会跳到下一圈。仅在目标之前、且总路线更短时使用。
            below = cycle_index(x, y - 1, n)
            if cells + below <= cap:
                south_plan = _route(below, cap - cells, n)
                if south_plan != None and (plan == None or 1 + _steps(south_plan) < _steps(plan)):
                    plan = [(South, 1)]
                    for segment in south_plan:
                        plan.append(segment)
    if plan == None:
        return advance_shortcut(index, budget, n, directions, runs)

    # 每段沿闭环正序前进，且终点恰好是预算上限。调用方再走连续尾长步。
    moved = 0
    for direction, count in plan:
        for step in range(count):
            if not move(direction):
                return cycle_index(get_pos_x(), get_pos_y(), n), moved + step, False
        moved += count
    return cap % cells, moved, True
