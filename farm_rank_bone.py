from farm_bones import advance_shortcut, cycle_index, cycle_tape, fast_tail, run_bones
from farm_bone_shortcut import fast_prefix
from farm_bone_rail import cycle_loop
from farm_route import go


def _follow(index, distance, directions, runs, cells, variant):
    # Move straight along each segment and validate the position at the next apple.
    while distance > 0:
        direction = directions[index]
        count = min(distance, runs[index])
        remainder = count
        if variant == 3 and count >= 8:
            # Unroll long straight segments to reduce the interpreter ticks spent on loop overhead.
            for block in range(count // 8):
                move(direction)
                move(direction)
                move(direction)
                move(direction)
                move(direction)
                move(direction)
                move(direction)
                move(direction)
            remainder = count % 8
        for step in range(remainder):
            move(direction)
        index += count
        if index == cells:
            index = 0
        distance -= count


def rank_tail(n, goal, directions, runs, variant):
    if variant == 1:
        return fast_tail(n, goal, directions, runs)
    cells = n * n
    index = n - 1
    moves = 0
    for length in range(1, goal):
        if get_entity_type() != Entities.Apple:
            return moves, "missing apple"
        next_apple = measure()
        if next_apple == None:
            return moves, "missing next apple"
        x, y = next_apple
        target = cycle_index(x, y, n)
        distance = (target - index) % cells
        if distance == 0 or distance > cells - length:
            return moves, "apple outside free arc"
        # Follow the cycle for the last length steps so the shortcut gaps fall behind the tail.
        if distance > length + 1:
            prefix = advance_shortcut
            if variant >= 4:
                prefix = fast_prefix
            index, advanced, ok = prefix(index, distance - length, n, directions, runs)
            moves += advanced
            if not ok:
                return moves, "blocked shortcut"
            distance = (target - index) % cells
        _follow(index, distance, directions, runs, cells, variant)
        moves += distance
        index = target
    if get_entity_type() == Entities.Apple and move(directions[index]):
        return moves + 1, "target reached"
    return moves, "final apple not collected"


def run_rank_bone(target, variant=3):
    if variant == 1:
        return run_bones(1, True)
    n = get_world_size()
    level = num_unlocked(Unlocks.Dinosaurs)
    if n != 32 or level == 0:
        return False
    # The game starts leaderboard runs on a fresh field. The daily entry point checks the field and inventory.
    cost = get_cost(Entities.Apple)
    for item in cost:
        if num_items(item) < cost[item] * (n * n - 1):
            return False
    if variant >= 5:
        # Start the perimeter route at the southwest corner. Variant 6 stops at intermediate apples. Variant 7 keeps each sweep intact.
        if not go(0, 0, n):
            return False
        before = num_items(Items.Bone)
        change_hat(Hats.Dinosaur_Hat)
        cycle_loop(variant - 5)
        change_hat(Hats.Straw_Hat)
        gain = num_items(Items.Bone) - before
        quick_print("[RANK BONE]", "variant", variant, "gain", gain, "target", target)
        return num_items(Items.Bone) >= target
    if not go(n - 1, 0, n):
        return False
    directions, runs = cycle_tape(n)
    before = num_items(Items.Bone)
    change_hat(Hats.Dinosaur_Hat)
    moves, status = rank_tail(n, n * n - 1, directions, runs, variant)
    change_hat(Hats.Straw_Hat)
    gain = num_items(Items.Bone) - before
    quick_print("[RANK BONE]", "variant", variant, "moves", moves, "gain", gain, "status", status)
    return status == "target reached" and num_items(Items.Bone) >= target
