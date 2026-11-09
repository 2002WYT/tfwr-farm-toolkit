from farm_gold import explore_maze, follow_tree, gold_geometry, gold_surface, run_gold
from farm_route import go, parallel


# 思路参考公开的独立小迷宫与动态地图讨论。本实现使用自己的布局和双向搜索。
# https://steamcommunity.com/app/2060160/discussions/0/570417860284821148/
# https://github.com/enihsyou/The-Farmer-Was-Replaced/blob/main/maze_single.py
# https://www.reddit.com/r/TheFarmerWasReplaced/comments/1p1nnmk/top_50_maze_single_leaderboard_code_with/


def cell_id(point, left, bottom, side):
    return (point[1] - bottom) * side + point[0] - left


def maze_graph(tree, left, bottom, side):
    links = []
    walls = []
    seen_start = []
    seen_target = []
    from_start = []
    from_target = []
    for cell in range(side * side):
        links.append([])
        walls.append([])
        seen_start.append(0)
        seen_target.append(0)
        from_start.append(None)
        from_target.append(None)
    for point in tree:
        cell = cell_id(point, left, bottom, side)
        previous, direction = tree[point]
        if previous != None:
            neighbor = cell_id(previous, left, bottom, side)
            links[neighbor].append((cell, direction))
            links[cell].append((neighbor, (direction + 2) % 4))
    for cell in range(side * side):
        x = cell % side
        y = cell // side
        adjacent = [cell + side, cell + 1, cell - side, cell - 1]
        inside = [y < side - 1, x < side - 1, y > 0, x > 0]
        for direction in range(4):
            edge = (adjacent[direction], direction)
            if inside[direction] and edge not in links[cell]:
                walls[cell].append(edge)
    return (links, walls), (seen_start, seen_target, from_start, from_target)


def two_way_path(links, start, target, stamp, search):
    # 按层扩展较短的队列。时间戳避免每次清空两份访问记录。
    seen_start, seen_target, from_start, from_target = search
    seen_start[start] = stamp
    seen_target[target] = stamp
    frontier = [start]
    opposite = [target]
    seen = seen_start
    seen_opposite = seen_target
    parents = from_start
    other_parents = from_target
    meeting = None
    while meeting == None and len(frontier) > 0 and len(opposite) > 0:
        if len(frontier) > len(opposite):
            frontier, opposite = opposite, frontier
            seen, seen_opposite = seen_opposite, seen
            parents, other_parents = other_parents, parents
        next_frontier = []
        for cell in frontier:
            for neighbor, direction in links[cell]:
                if seen[neighbor] != stamp:
                    seen[neighbor] = stamp
                    parents[neighbor] = (cell, direction)
                    if seen_opposite[neighbor] == stamp:
                        meeting = neighbor
                        break
                    next_frontier.append(neighbor)
            if meeting != None:
                break
        frontier = next_frontier
    if meeting == None:
        return None

    path = []
    cell = meeting
    while cell != target:
        cell, direction = from_target[cell]
        path.append((direction + 2) % 4)
    reversed_path = []
    for index in range(len(path) - 1, -1, -1):
        reversed_path.append(path[index])
    cell = meeting
    while cell != start:
        cell, direction = from_start[cell]
        reversed_path.append(direction)
    return reversed_path


def straight_path(links, start, target, side):
    # 只在已知通道上试走曼哈顿距离；成功时路线已经最短。
    horizontal = target % side - start % side
    vertical = target // side - start // side
    horizontal_direction = 1
    if horizontal < 0:
        horizontal_direction = 3
    vertical_direction = 0
    if vertical < 0:
        vertical_direction = 2
    horizontal = abs(horizontal)
    vertical = abs(vertical)
    path = []
    while start != target:
        next_cell = None
        for neighbor, direction in links[start]:
            if direction == horizontal_direction and horizontal > 0:
                horizontal -= 1
            elif direction == vertical_direction and vertical > 0:
                vertical -= 1
            else:
                continue
            next_cell = neighbor
            path.append(direction)
            break
        if next_cell == None:
            return None
        start = next_cell
    reversed_path = []
    for index in range(len(path) - 1, -1, -1):
        reversed_path.append(path[index])
    return reversed_path


def walk_rank_path(graph, search, start, target, stamp, side, directions, variant):
    links, walls = graph
    path = None
    if variant == 3 and stamp >= 100 and side >= 8:
        path = straight_path(links, start, target, side)
    if path == None:
        path = two_way_path(links, start, target, stamp, search)
    if path == None:
        return False

    probe = stamp % 5 == 0
    if variant == 3:
        probe = stamp % 3 == 0
    offsets = [side, 1, -side, -1]
    cell = start
    for index in range(len(path) - 1, -1, -1):
        if probe:
            # 拆墙只会增添通道。每发现一条边，就从两端的待测名单移除。
            candidates = walls[cell]
            for wall in range(len(candidates) - 1, -1, -1):
                neighbor, direction = candidates[wall]
                if can_move(directions[direction]):
                    candidates.pop(wall)
                    reverse = (cell, (direction + 2) % 4)
                    walls[neighbor].remove(reverse)
                    links[cell].append((neighbor, direction))
                    links[neighbor].append(reverse)
        direction = path[index]
        if not move(directions[direction]):
            return False
        cell += offsets[direction]
    return True


def rank_maze_worker(worker, n, workers, config):
    rounds, grid, side, substance, start_at, variant, shared_target = config
    left = worker % grid * side
    bottom = worker // grid * side
    anchor = (left + side // 2, bottom + side // 2)
    if not go(anchor[0], anchor[1], n):
        return 0
    # 密排地块没有走廊。所有无人机先到种植点，然后才允许生成迷宫。
    while get_time() + 1.05 < start_at:
        do_a_flip()
    while get_time() < start_at:
        pass

    directions = [North, East, South, West]
    collected = 0
    while collected < rounds or shared_target > 0:
        if shared_target > 0 and num_items(Items.Gold) >= shared_target:
            return collected
        if not go(anchor[0], anchor[1], n) or not plant(Entities.Bush):
            return collected
        if not use_item(Items.Weird_Substance, substance):
            return collected
        remaining = min(301, rounds - collected)
        if shared_target > 0:
            remaining = 301
        treasure = measure()
        if treasure == None:
            return collected
        if remaining == 1:
            if explore_maze(anchor, treasure, left, bottom, side, directions) == None:
                return collected
        else:
            tree = explore_maze(anchor, None, left, bottom, side, directions)
            if tree == None or not follow_tree(tree, anchor, treasure, directions):
                return collected
            if variant == 3 or workers == 1:
                graph, search = maze_graph(tree, left, bottom, side)

        for pickup in range(remaining):
            if get_entity_type() != Entities.Treasure:
                return collected
            # 多机共享金币目标。达标后每架无人机收掉自己的最后一箱即可结束。
            if pickup == remaining - 1 or (shared_target > 0 and num_items(Items.Gold) >= shared_target):
                if not harvest():
                    return collected
                collected += 1
                break
            else:
                if not use_item(Items.Weird_Substance, substance):
                    return collected
                collected += 1
                target = measure()
                for retry in range(100):
                    if target != None and target != treasure:
                        break
                    target = measure()
                if target == None or target == treasure:
                    return collected
                if (variant == 3 or workers == 1) and pickup >= 8:
                    start_cell = cell_id(treasure, left, bottom, side)
                    target_cell = cell_id(target, left, bottom, side)
                    if not walk_rank_path(graph, search, start_cell, target_cell,
                                          pickup + 1, side, directions, variant):
                        return collected
                elif not follow_tree(tree, treasure, target, directions):
                    return collected
                treasure = target
    return collected


def run_rank_maze(single, target, variant=3):
    # 1 沿用生产路线；2 密排或双向寻路；3 多机共享目标，单机尝试已知直达路径。
    if variant != 1 and variant != 2 and variant != 3:
        quick_print("[MAZE RANK STOP]", "unknown variant", variant)
        return False
    started = get_time()
    before = num_items(Items.Gold)
    if before >= target:
        return True
    n = get_world_size()
    level = num_unlocked(Unlocks.Mazes)
    if level == 0:
        quick_print("[MAZE RANK STOP]", "maze research required")
        return False
    if num_unlocked(Unlocks.Megafarm) > 0 and num_drones() != 1:
        quick_print("[MAZE RANK STOP]", "finish the other drones before starting")
        return False
    workers = 0
    if single:
        workers = 1
    workers, grid, stride, side = gold_geometry(n, workers)
    if variant != 1 and workers > 1:
        side = n // grid
    factor = 2 ** (level - 1)
    substance = side * factor
    per_round = workers * side * substance
    rounds = (target - before + per_round - 1) // per_round
    shared_target = 0
    expected_gold = rounds * per_round
    if variant == 1:
        ok = run_gold(rounds, workers)
    else:
        budget = rounds * workers
        if variant == 3 and workers > 1:
            shared_target = target
            # 到达目标时，至多每架无人机各有一次正在结算的移动和一次收尾收获。
            budget = (target - before + side * substance - 1) // (side * substance) + 2 * workers
        required_cost = budget * substance
        before_substance = num_items(Items.Weird_Substance)
        if before_substance < required_cost:
            quick_print("[MAZE RANK STOP]", "weird substance", before_substance, "need", required_cost)
            return False
        for clean in parallel(gold_surface, n, min(n, workers), None):
            if not clean:
                quick_print("[MAZE RANK STOP]", "surface must contain only empty ground and grass")
                return False
        if not go(0, 0, n):
            return False
        start_at = get_time()
        if workers > 1:
            # 移动及生成无人机都是 200 ticks。预留失去电力后减速的余量。
            measured_at = get_time()
            if not move(East):
                return False
            action_time = get_time() - measured_at
            if not move(West):
                return False
            start_at = get_time() + (n + workers + 8) * action_time * 2
        pickups = 0
        config = (rounds, grid, side, substance, start_at, variant, shared_target)
        for count in parallel(rank_maze_worker, n, workers, config):
            pickups += count
        spent = before_substance - num_items(Items.Weird_Substance)
        ok = pickups == workers * rounds and spent == required_cost
        if shared_target > 0:
            expected_gold = pickups * side * substance
            ok = spent == pickups * substance and pickups <= budget
    gain = num_items(Items.Gold) - before
    quick_print("[MAZE RANK]", "variant", variant, "workers", workers, "side", side,
                "planned_rounds", rounds, "gold", gain, "expected", expected_gold,
                "seconds", get_time() - started)
    return ok and gain == expected_gold and num_items(Items.Gold) >= target
