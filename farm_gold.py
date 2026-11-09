from farm_route import go, parallel


def gold_surface(worker, n, workers, unused):
    first = worker * n // workers
    end = (worker + 1) * n // workers
    for y in range(first, end):
        for column in range(n):
            x = column
            if (y - first) % 2 == 1:
                x = n - 1 - column
            if not go(x, y, n):
                return False
            ground = get_ground_type()
            entity = get_entity_type()
            if ground != Grounds.Grassland and ground != Grounds.Soil:
                return False
            if entity != None and entity != Entities.Grass:
                return False
    return True


def explore_maze(start, target, left, bottom, side, directions):
    # Follow actual passages. Each entry records the direction from its parent.
    offsets = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    parents = {start: (None, 0)}
    choices = [0]
    current = start
    while len(choices) > 0:
        if current == target:
            return parents
        direction = choices[-1]
        if direction == 4:
            choices.pop()
            if len(choices) > 0:
                previous, incoming = parents[current]
                if not move(directions[(incoming + 2) % 4]):
                    return None
                current = previous
        else:
            choices[-1] += 1
            dx, dy = offsets[direction]
            x = current[0] + dx
            y = current[1] + dy
            neighbor = (x, y)
            if (left <= x and x < left + side and bottom <= y and y < bottom + side
                    and neighbor not in parents and move(directions[direction])):
                parents[neighbor] = (current, direction)
                choices.append(0)
                current = neighbor
    if target == None and len(parents) == side * side:
        return parents
    return None


def follow_tree(parents, start, target, directions):
    if target not in parents:
        return False
    ancestors = set()
    node = start
    while node != None:
        ancestors.add(node)
        node = parents[node][0]

    downward = []
    node = target
    while node not in ancestors:
        previous, direction = parents[node]
        downward.append(direction)
        node = previous

    while start != node:
        previous, direction = parents[start]
        if not move(directions[(direction + 2) % 4]):
            return False
        start = previous
    for i in range(len(downward) - 1, -1, -1):
        if not move(directions[downward[i]]):
            return False
    return True


def maze_links(parents):
    links = {}
    for cell in parents:
        links[cell] = [None, None, None, None]
    for cell in parents:
        previous, direction = parents[cell]
        if previous != None:
            links[previous][direction] = cell
            links[cell][(direction + 2) % 4] = previous
    return links


def maze_distance(cell, target):
    return abs(cell[0] - target[0]) + abs(cell[1] - target[1])


def shortest_maze_path(links, start, target):
    # A Manhattan heuristic changes by one per step, so the A* estimate stays put or rises by two.
    # Group equal estimates in buckets to avoid sorting the entire search queue.
    priority = maze_distance(start, target)
    buckets = {priority: [(start, 0)]}
    distance = {start: 0}
    previous = {}
    bound = len(links)
    while priority < bound:
        if priority not in buckets or len(buckets[priority]) == 0:
            priority += 2
            continue
        cell, cost = buckets[priority].pop()
        if cost != distance[cell]:
            continue
        if cell == target:
            path = []
            while cell != start:
                parent, direction = previous[cell]
                path.append((cell, direction))
                cell = parent
            return path
        next_cost = cost + 1
        adjacent = links[cell]
        for direction in range(4):
            neighbor = adjacent[direction]
            if neighbor != None and (neighbor not in distance or next_cost < distance[neighbor]):
                distance[neighbor] = next_cost
                previous[neighbor] = (cell, direction)
                next_priority = next_cost + maze_distance(neighbor, target)
                if next_priority not in buckets:
                    buckets[next_priority] = []
                buckets[next_priority].append((neighbor, next_cost))
    return None


def follow_maze_path(links, start, target, directions, probe):
    path = shortest_maze_path(links, start, target)
    if path == None:
        return False
    offsets = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    cell = start
    for index in range(len(path) - 1, -1, -1):
        if probe:
            # Moving treasure only removes walls. Add any corridors found along the route to the graph.
            adjacent = links[cell]
            for direction in range(4):
                if adjacent[direction] == None and can_move(directions[direction]):
                    dx, dy = offsets[direction]
                    neighbor = (cell[0] + dx, cell[1] + dy)
                    if neighbor in links:
                        adjacent[direction] = neighbor
                        links[neighbor][(direction + 2) % 4] = cell
        neighbor, direction = path[index]
        if not move(directions[direction]):
            return False
        cell = neighbor
    return True


def gold_worker(worker, n, workers, config):
    rounds, grid, stride, side, substance = config
    left = 0
    bottom = 0
    if workers > 1:
        left = worker % grid * stride + 1
        bottom = worker // grid * stride + 1
    # Mazes expand southwest first. Plant at the northeast tile of the central four for even sizes.
    x = left + side // 2
    y = bottom + side // 2
    anchor = (x, y)
    if workers > 1:
        # Approach along row zero and the plot's west corridor to stay out of neighboring mazes.
        if not go(left - 1, 0, n) or not go(left - 1, y, n):
            return 0

    directions = [North, East, South, West]
    collected = 0
    while collected < rounds:
        if not go(x, y, n) or not plant(Entities.Bush):
            return collected
        if not use_item(Items.Weird_Substance, substance):
            return collected

        remaining = min(rounds - collected, 301)
        links = None
        target = measure()
        if target == None:
            return collected
        if remaining == 1:
            if explore_maze(anchor, target, left, bottom, side, directions) == None:
                return collected
        else:
            parents = explore_maze(anchor, None, left, bottom, side, directions)
            if parents == None or not follow_tree(parents, anchor, target, directions):
                return collected
            # For small mazes and short runs, follow the original tree to avoid repeated graph searches.
            if side >= 8 and remaining >= 24:
                links = maze_links(parents)

        for pickup in range(remaining):
            if get_entity_type() != Entities.Treasure:
                return collected
            if pickup == remaining - 1:
                if not harvest():
                    return collected
            else:
                if not use_item(Items.Weird_Substance, substance):
                    return collected
                # Wait for the Weird Substance action to finish so the treasure has moved to a different tile.
                next_target = measure()
                for retry in range(100):
                    if next_target != None and next_target != target:
                        break
                    next_target = measure()
                if next_target == None or next_target == target:
                    return collected + 1
                if links != None and pickup >= 12:
                    if not follow_maze_path(links, target, next_target, directions, pickup % 3 == 0):
                        return collected + 1
                elif not follow_tree(parents, target, next_target, directions):
                    return collected + 1
                target = next_target
            collected += 1
    return collected


def gold_geometry(n, workers):
    # Leave a west corridor beside each maze and use sides of at least two tiles so treasure can move.
    limit = 1
    if num_unlocked(Unlocks.Megafarm) > 0:
        limit = min(max_drones(), max(1, n // 3) ** 2)
    if workers == 0:
        workers = limit
    else:
        workers = min(workers, limit)
    grid = 1
    while grid * grid < workers:
        grid += 1
    stride = n // grid
    side = n
    if workers > 1:
        side = stride - 1
    return workers, grid, stride, side


def run_gold(rounds, workers):
    n = get_world_size()
    level = num_unlocked(Unlocks.Mazes)
    if rounds < 1 or rounds % 1 != 0 or workers < 0 or workers % 1 != 0 or level == 0:
        quick_print("[GOLD STOP]", "requires maze research and whole-number rounds and workers",
                    level, rounds, workers)
        return False
    if num_unlocked(Unlocks.Megafarm) > 0 and num_drones() != 1:
        quick_print("[GOLD STOP]", "finish the other drones before starting")
        return False
    workers, grid, stride, side = gold_geometry(n, workers)
    factor = 2 ** (level - 1)
    substance = side * factor
    expected_pickups = rounds * workers
    expected_gold = expected_pickups * side * side * factor
    expected_cost = expected_pickups * substance
    before_substance = num_items(Items.Weird_Substance)
    if before_substance < expected_cost:
        quick_print("[GOLD STOP]", "weird substance", "need", expected_cost, "have", before_substance)
        return False

    started = get_time()
    before_gold = num_items(Items.Gold)
    for ok in parallel(gold_surface, n, min(n, workers), None):
        if not ok:
            quick_print("[GOLD STOP]", "surface must contain only empty ground and grass")
            return False
    if not go(0, 0, n):
        quick_print("[GOLD STOP]", "cannot reach the start")
        return False

    collected = 0
    config = (rounds, grid, stride, side, substance)
    for count in parallel(gold_worker, n, workers, config):
        collected += count
    gain = num_items(Items.Gold) - before_gold
    spent = before_substance - num_items(Items.Weird_Substance)
    elapsed = get_time() - started
    quick_print("[GOLD]", "workers", workers, "maze_side", side, "rounds", rounds,
                "pickups", collected, "gold", gain, "expected", expected_gold,
                "substance", spent, "seconds", elapsed)
    if elapsed > 0:
        quick_print("[RATE]", Items.Gold, "net_per_min", gain * 60 / elapsed)
    if collected != expected_pickups or gain != expected_gold or spent != expected_cost:
        quick_print("[GOLD STOP]", "incomplete maze batch")
        return False
    return True
