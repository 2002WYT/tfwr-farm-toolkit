from farm_route import go, parallel


def empty_stripe(worker, n, workers, unused):
    for y in range(worker * n // workers, (worker + 1) * n // workers):
        for column in range(n):
            x = column
            if y % 2 == 1:
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


def cycle_segments(n, at_origin=False):
    # Keep the west edge for the return leg.
    segments = []
    if at_origin:
        segments.append((East, n - 1))
    for y in range(1, n):
        segments.append((North, 1))
        if y == n - 1:
            segments.append((West, n - 1))
        elif y % 2 == 1:
            segments.append((West, n - 2))
        else:
            segments.append((East, n - 2))
    segments.append((South, n - 1))
    if not at_origin:
        segments.append((East, n - 1))
    return segments


def cycle_index(x, y, n):
    if x == 0:
        return (n * n - y) % (n * n)
    if y % 2 == 0:
        return y * (n - 1) + x
    return y * (n - 1) + n - x


def cycle_tape(n):
    directions = []
    runs = []
    for direction, distance in cycle_segments(n, True):
        for left in range(distance, 0, -1):
            directions.append(direction)
            runs.append(left)
    return directions, runs


def advance_cycle(index, distance, directions, runs, cells):
    moved = 0
    while distance > 0:
        direction = directions[index]
        count = min(distance, runs[index])
        for step in range(count):
            if not move(direction):
                return moved + step
        moved += count
        index = (index + count) % cells
        distance -= count
    return moved


def advance_shortcut(index, distance, n, directions, runs):
    cells = n * n
    width = n - 1
    moved = 0
    while distance > 1:
        if index == 0 or index > width * width:
            # From the return leg, reach the next set of rows before jumping.
            count = 1
            if index != 0:
                count = cells - index + 1
            if count >= distance:
                break
            advanced = advance_cycle(index, count, directions, runs, cells)
            moved += advanced
            if advanced != count:
                return index, moved, False
            index = 1
            distance -= count
        y = (index - 1) // width
        x = index - y * width
        if y % 2 == 1:
            x = n - x
        # North goes forward in cycle order in each of the serpentine rows.
        cap = min(index + distance, n * width)
        top = (cap - 1) // width
        target = cycle_index(x, top, n)
        if target > cap:
            top -= 1
            target = cycle_index(x, top, n)
        if top <= y:
            break
        for step in range(top - y):
            if not move(North):
                return index, moved + step, False
        moved += top - y
        distance -= target - index
        index = target
    return index, moved, True


def fast_tail(n, goal, directions, runs, shortcuts=True):
    cells = n * n
    index = n - 1
    moved = 0
    for length in range(1, goal + 1):
        if get_entity_type() != Entities.Apple:
            return moved, "missing apple"
        if length == goal:
            if move(directions[index]):
                return moved + 1, "target reached"
            return moved, "blocked move"
        next_apple = measure()
        if next_apple == None:
            if move(directions[index]):
                moved += 1
            return moved, "missing next apple"
        x, y = next_apple
        target = cycle_index(x, y, n)
        distance = (target - index) % cells
        # At each apple the tail is contiguous. Its tip lies beyond the next apple.
        if distance == 0 or distance > cells - length:
            return moved, "apple outside free arc"
        # The last `length` unit moves flush any gap introduced by a shortcut.
        if shortcuts and distance > length + 1:
            index, advanced, ok = advance_shortcut(index, distance - length, n, directions, runs)
            moved += advanced
            if not ok:
                return moved, "blocked shortcut"
            distance = (target - index) % cells
        advanced = advance_cycle(index, distance, directions, runs, cells)
        moved += advanced
        if advanced != distance:
            return moved, "blocked move"
        index = target
    return moved, "target reached"


def full_tail(segments, cells):
    moves = 0
    for circuit in range(cells):
        cactus = num_items(Items.Cactus)
        for direction, distance in segments:
            for step in range(distance):
                if not move(direction):
                    return moves + step, "cycle stopped"
            moves += distance
        if num_items(Items.Cactus) == cactus:
            return moves, "no new apple"
    return moves, "circuit limit"


def counted_tail(segments, goal):
    moves = 0
    length = 0
    for circuit in range(goal + 1):
        before = length
        for direction, distance in segments:
            for step in range(distance):
                eating = get_entity_type() == Entities.Apple
                if not move(direction):
                    return moves, "cycle stopped"
                moves += 1
                if eating:
                    length += 1
                    if length == goal:
                        return moves, "target reached"
        if length == before:
            return moves, "no new apple"
    return moves, "circuit limit"


def run_bones(rounds, bulk, fast=True, tail_override=()):
    n = get_world_size()
    level = num_unlocked(Unlocks.Dinosaurs)
    if rounds < 1 or level == 0 or n < 2 or n % 2 != 0:
        quick_print("[BONE STOP]", "requires Dinosaur research, an even surface and positive rounds", n, level)
        return False
    cost = get_cost(Entities.Apple)
    for item in cost:
        if num_items(item) < cost[item]:
            quick_print("[BONE STOP]", "apple budget", item, "need", cost[item], "have", num_items(item))
            return False
    for ok in parallel(empty_stripe, n, min(n, max_drones()), None):
        if not ok:
            quick_print("[BONE STOP]", "surface must be empty or grass")
            return False

    cells = n * n
    segments = cycle_segments(n)
    if bulk and fast:
        directions, runs = cycle_tape(n)
    multiplier = 2 ** (level - 1)
    for batch in range(1, rounds + 1):
        goal = cells - 1
        for item in cost:
            goal = min(goal, num_items(item) // cost[item])
        if goal < 1:
            quick_print("[BONE STOP]", "apple budget", "batch", batch)
            return False
        if not go(n - 1, 0, n):
            quick_print("[BONE STOP]", "cannot reach starting corner")
            return False

        start = get_time()
        before_bone = num_items(Items.Bone)
        before_cactus = num_items(Items.Cactus)
        change_hat(Hats.Dinosaur_Hat)
        moves = 0
        status = "missing first apple"
        if get_entity_type() == Entities.Apple:
            if bulk and fast:
                if len(tail_override) == 0:
                    moves, status = fast_tail(n, goal, directions, runs)
                else:
                    solve_tail = tail_override[0]
                    moves, status = solve_tail(n, goal, directions, runs)
            elif bulk and goal == cells - 1:
                moves, status = full_tail(segments, cells)
            else:
                moves, status = counted_tail(segments, goal)
        change_hat(Hats.Straw_Hat)

        elapsed = get_time() - start
        gain = num_items(Items.Bone) - before_bone
        expected = goal ** 2 * multiplier
        if gain == expected:
            status = "target reached"
        quick_print("[BONE]", "batch", batch, "level", level, "apples_eaten", (gain / multiplier) ** 0.5,
                    "target", goal, "moves", moves, "cactus_spent", before_cactus - num_items(Items.Cactus),
                    "bones", gain, "expected", expected, "seconds", elapsed, "status", status)
        if elapsed > 0:
            quick_print("[RATE]", Items.Bone, "net_per_min", gain * 60 / elapsed)
        if gain != expected:
            return False
    return True
