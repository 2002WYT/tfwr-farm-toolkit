def directions():
    return (North, East, South, West)


def go_to(x, y):
    n = get_world_size()
    dx = (x - get_pos_x()) % n
    dy = (y - get_pos_y()) % n
    horizontal = East
    vertical = North
    if dx * 2 > n:
        dx = n - dx
        horizontal = West
    if dy * 2 > n:
        dy = n - dy
        vertical = South
    for i in range(dx):
        if not move(horizontal):
            return False
    for i in range(dy):
        if not move(vertical):
            return False
    return True


def drop_to(z):
    while get_pos_z() > z:
        if not dig_one():
            return False
    return get_pos_z() == z


def seek(ground, limit):
    for i in range(limit):
        current = get_ground_type()
        if current == ground:
            return True
        if not dig_one():
            return False
    return get_ground_type() == ground


def dig_one():
    if get_ground_type() == Grounds.Bedrock:
        return False
    for attempt in range(64):
        if dig():
            return True
    return False


def worker_count(workers, jobs):
    count = 1
    if num_unlocked(Unlocks.Megafarm):
        count = max_drones()
        if workers > 0:
            count = min(count, workers)
    return min(count, jobs)


def row_batch(task, rows, start, end, args):
    result = 0
    for index in range(start, end):
        row = rows[index]
        if go_to(get_pos_x(), row):
            if len(args) == 0:
                result += task(row)
            elif len(args) == 1:
                result += task(row, args[0])
            elif len(args) == 2:
                result += task(row, args[0], args[1])
            elif len(args) == 3:
                result += task(row, args[0], args[1], args[2])
    return result


def run_rows(task, rows, workers, args):
    count = worker_count(workers, len(rows))
    if count <= 1:
        return row_batch(task, rows, 0, len(rows), args)

    drones = []
    pending = []
    for rank in range(count - 1):
        start = rank * len(rows) // count
        end = (rank + 1) * len(rows) // count
        go_to(get_pos_x(), rows[start])
        drone = spawn_drone(row_batch, task, rows, start, end, args)
        if drone:
            drones.append(drone)
        else:
            pending.append((start, end))

    result = row_batch(task,
        rows, (count - 1) * len(rows) // count, len(rows), args)
    for start, end in pending:
        result += row_batch(task, rows, start, end, args)
    for drone in drones:
        result += wait_for(drone)
    return result


def fork_jobs(task, jobs, first, last, count):
    if count <= 1:
        total = 0
        for index in range(first, last):
            total += task(jobs[index])
        return total

    left_count = count // 2
    middle = first + (last - first) * left_count // count
    drone = spawn_drone(fork_jobs,
        task, jobs, middle, last, count - left_count)
    total = fork_jobs(task, jobs, first, middle, left_count)
    if drone:
        return total + wait_for(drone)
    return total + fork_jobs(task, jobs, middle, last, count - left_count)


def run_jobs(task, jobs, workers):
    return (fork_jobs(task,
        jobs, 0, len(jobs), worker_count(workers, len(jobs))))




def water_crop():
    if not num_unlocked(Unlocks.Watering):
        return 0
    water = get_water()
    if water < 0.96:
        tanks = min(num_items(Items.Water), 4 - (water * 4) // 1)
        if tanks > 0 and use_item(Items.Water, tanks):
            water = get_water()
    return water


def find_clay(limit_z):
    while get_ground_type() != Grounds.Clay:
        if get_pos_z() <= limit_z or get_ground_type() == Grounds.Rock:
            return False
        if not dig_one():
            return False
    return True


def prepare_rice_row(row, depth, size, first_layer):
    ready = 0
    for i in range(size):
        if first_layer:
            find_clay(depth - 4)
        elif get_ground_type() == Grounds.Dry_Rice_Terrace:
            dig_one()
        if get_ground_type() == Grounds.Clay:
            ready += 1
        if i + 1 < size and not move(East):
            break
    return ready


def rice_row(row, size):
    cells = []
    for i in range(size):
        if get_ground_type() == Grounds.Clay and plant(Entities.Rice):
            water_crop()
            cells.append(get_pos_x())
        if i + 1 < size and not move(East):
            break

    # Harvest in planting order. No drone can dig during this wave.
    harvested = 0
    for x in cells:
        if not go_to(x, row) or get_entity_type() != Entities.Rice:
            continue
        while get_entity_type() == Entities.Rice and not can_harvest():
            wait_until(get_time() + 0.2)
        if get_entity_type() != Entities.Rice or not harvest():
            continue
        harvested += 1
    return harvested


def rice_round(workers):
    if not find_clay(get_pos_z() - 32):
        return 0
    size = get_world_size()
    rows = []
    for row in range(size):
        rows.append(row)
    depth = get_pos_z()
    first_layer = True
    total = 0
    while (run_rows(prepare_rice_row,
        rows, workers, (depth, size, first_layer)) > 0):
        cut = run_rows(rice_row, rows, workers, (size,))
        if cut == 0:
            break
        total += cut
        first_layer = False
    return total


def wait_until(ready):
    while get_time() + 1 <= ready:
        do_a_flip()
    while get_time() < ready:
        pass


def set_hover(height):
    return get_hover() == height or hover(height)


def bamboo_ready(segments, water, watered_at):
    now = get_time()
    if water > 0:
        # The game can decay water by 1% every 0.1 seconds. Use that
        # worst case to avoid cutting the final stalk before it is ready.
        decay_steps = (now - watered_at + segments) * 10 + 2
        segments = segments / (1 + 4 * water * 0.99 ** decay_steps)
    return now + segments


def find_perlite(limit_z):
    while get_ground_type() != Grounds.Perlite:
        if get_pos_z() <= limit_z or get_ground_type() == Grounds.Dynamite:
            return False
        if not dig_one():
            return False
    return True


def plant_bamboo(cells, toward, back, perlite_depth):
    if not move(toward):
        return
    if perlite_depth != None:
        if not find_perlite(perlite_depth - 5):
            move(back)
            return
    elif get_ground_type() == Grounds.Grassland:
        till()
    if get_entity_type() == Entities.Bamboo or plant(Entities.Bamboo):
        watered_at = get_time()
        water = water_crop()
        fruit = measure()
        x = get_pos_x()
        move(back)
        if fruit != None:
            ready = bamboo_ready(fruit, water, watered_at)
            cells.append((x,
                fruit, 0, ready, 0, toward, back, water, watered_at))
    else:
        move(back)


def next_bamboo(cells, x, size):
    best = -1
    best_distance = size
    first = 0
    now = get_time()
    for i in range(len(cells)):
        cell = cells[i]
        if cell[3] < cells[first][3]:
            first = i
        if cell[3] <= now:
            distance = abs(x - cell[0])
            distance = min(distance, size - distance)
            if distance < best_distance:
                best = i
                best_distance = distance
                if distance == 0:
                    return best
    if best != -1:
        return best
    return first


def bamboo_row(lane, rounds, size, perlite_depth):
    harvested = 0
    double_sided = lane < 3 * (size // 3)
    for round_index in range(rounds):
        cells = []
        set_hover(1)
        for i in range(size):
            plant_bamboo(cells, South, North, perlite_depth)
            if double_sided:
                plant_bamboo(cells, North, South, perlite_depth)
            if i + 1 < size:
                move(East)

        cut = 0
        while len(cells) > 0:
            index = next_bamboo(cells, get_pos_x(), size)
            (x, fruit, plucked, ready,
                retries, toward, back, water, watered_at) = (cells[index])
            if (not go_to(x,
                lane) or get_entity_type(toward) != Entities.Bamboo):
                cells.pop(index)
                continue
            wait_until(ready)
            # The first two fruits stop growth. Cut at the base only once the
            # third fruit has had time to grow, to collect the full squared
            # yield.
            height = fruit
            if plucked == 2:
                height = 0
            if set_hover(height):
                move(toward)
                if get_pos_y() != lane:
                    move(back)
            new_fruit = measure(toward)
            if get_entity_type(toward) != Entities.Bamboo:
                cut += 1
                cells.pop(index)
            elif plucked < 2 and new_fruit != None and new_fruit > fruit:
                ready = bamboo_ready(new_fruit - fruit, water, watered_at)
                cells[index] = (x, new_fruit,
                    plucked + 1, ready, 0, toward, back, water, watered_at)
            elif retries < 5:
                ready = get_time() + 0.5
                cells[index] = (x, fruit, plucked,
                    ready, retries + 1, toward, back, water, watered_at)
            else:
                cells.pop(index)
        harvested += cut
        if cut == 0:
            break
    return harvested


def bamboo_plot(rounds, workers, perlite_depth):
    size = get_world_size()
    rows = []
    for index in range(size // 3):
        rows.append(3 * index + 1)
    if size % 3 == 2:
        rows.append(size - 1)
    return run_rows(bamboo_row, rows, workers, (rounds, size, perlite_depth))


def bamboo_run(rounds, workers):
    return bamboo_plot(rounds, workers, None)


def bamboo_perlite_run(rounds, workers):
    if num_unlocked(Unlocks.Jump):
        jump(Unlocks.Special_Soils)
    if find_perlite(get_pos_z() - 32):
        cut = bamboo_plot(rounds, workers, get_pos_z())
        if cut > 0:
            return cut
    quick_print("No perlite bamboo harvested; using surface soil.")
    clear()
    return bamboo_run(rounds, workers)



# Adapted from Semy0nBu/the-farmer-was-replaced (MIT). See LICENSE-MIT.txt.

ds = [North,East,South,West]
xs = [0,1,0,-1]
ys = [1,0,-1,0]

def seek_mushroom(size):
    for step in range(1024):
        if get_world_size() != size or get_ground_type() == Grounds.Bedrock:
            return False
        if get_ground_type() == Grounds.Mushroom:
            return True
        if get_ground_type() == Grounds.Limestone:
            if not move(East):
                return False
        elif not dig_one():
            return False
    return get_ground_type() == Grounds.Mushroom

def remember(a,zs,cnt,index,kind,z):
    old = a[index]
    if old != kind:
        if old >= 0:
            cnt[old] -= 1
        if kind >= 0:
            cnt[kind] += 1
        a[index] = kind
    zs[index] = z

def snapshot(a,zs,cnt,ox,oy,width,height,floor):
    x = get_pos_x() - ox
    y = get_pos_y() - oy
    for side in range(5):
        tx = x
        ty = y
        dir = None
        if side < 4:
            tx += xs[side]
            ty += ys[side]
            dir = ds[side]
        if tx < 0 or tx >= width or ty < 0 or ty >= height:
            continue
        kind = -1
        z = get_pos_z(dir)
        if z >= floor and get_ground_type(dir) == Grounds.Mushroom:
            value = measure(dir)
            if value != None:
                kind = value
        remember(a,zs,cnt,ty * width + tx,kind,z)

def go(index,ox,oy,width,size):
    return go_to(ox + index % width, oy + index // width)

def prepare(z,a,zs,cnt,ox,oy,width,height,floor,size):
    for step in range(128):
        if get_world_size() != size:
            return False
        here = get_pos_z()
        if here == z:
            snapshot(a,zs,cnt,ox,oy,width,height,floor)
            return True
        if here > z:
            if not dig_one():
                return False
        else:
            if not place(Grounds.Dirt):
                return False
    return False

def fixture(source,target,a,zs,cnt,ox,oy,width,height,floor,size):
    x = target % width
    y = target // width
    z = zs[target]
    best = -1
    cost = 100000
    for way in range(4):
        tx = x + xs[way]
        ty = y + ys[way]
        if tx < 0 or tx >= width or ty < 0 or ty >= height:
            continue
        index = ty * width + tx
        if index == source:
            continue
        value = abs(tx - source % width) + abs(ty - source // width)
        if a[index] >= 0:
            value += 3
        if zs[index] > z - 2:
            value += zs[index] - z + 2
        if value < cost:
            best = way
            cost = value
    if best < 0:
        return -1
    index = (y + ys[best]) * width + x + xs[best]
    if (not go(index,ox,oy,width,
        size) or not prepare(z - 2,a,zs,cnt,ox,oy,width,height,floor,size)):
        return -1
    if not go(target,ox,oy,width,size):
        return -1
    kind = a[target]
    if (get_ground_type() != Grounds.Mushroom
        or measure() != kind or get_pos_z() != z):
        snapshot(a,zs,cnt,ox,oy,width,height,floor)
        return -1
    if not push(ds[best]):
        snapshot(a,zs,cnt,ox,oy,width,height,floor)
        return -1
    snapshot(a,zs,cnt,ox,oy,width,height,floor)
    if not move(ds[best]):
        return -1
    snapshot(a,zs,cnt,ox,oy,width,height,floor)
    if a[index] != kind or get_pos_z() != z - 1:
        return -2
    return index

def match(source,target,a,zs,cnt,ox,oy,width,height,floor,size):
    if not go(target,ox,oy,width,size):
        return False
    snapshot(a,zs,cnt,ox,oy,width,height,floor)
    kind = a[source]
    if kind < 0 or a[target] != kind:
        return False
    if zs[source] < zs[target]:
        old = source
        source = target
        target = old
        if not go(target,ox,oy,width,size):
            return False
        snapshot(a,zs,cnt,ox,oy,width,height,floor)
    if zs[source] == zs[target]:
        target = fixture(source,target,a,zs,cnt,ox,oy,width,height,floor,size)
        if target == -2:
            return True
        if target < 0:
            return False
    if not go(source,ox,oy,width,size):
        return False
    snapshot(a,zs,cnt,ox,oy,width,height,floor)
    if a[source] != kind:
        return False
    z = get_pos_z()
    for step in range(width + height + 2):
        x = get_pos_x() - ox
        y = get_pos_y() - oy
        tx = target % width
        ty = target // width
        way = 0
        if x < tx:
            way = 1
        elif x > tx:
            way = 3
        elif y > ty:
            way = 2
        elif y == ty:
            return False
        next = (y + ys[way]) * width + x + xs[way]
        if next != target:
            if (not go(next,ox,oy,width,size)
                or not prepare(z - 1,a,zs,cnt,ox,oy,width,height,floor,size)):
                return False
            if not go(y * width + x,ox,oy,width,size):
                return False
        else:
            if (get_ground_type(ds[way]) != Grounds.Mushroom
                or measure(ds[way]) != kind or get_pos_z(ds[way]) >= z):
                return False
        if (get_ground_type() != Grounds.Mushroom
            or measure() != kind or get_pos_z() != z):
            snapshot(a,zs,cnt,ox,oy,width,height,floor)
            return False
        if not push(ds[way]):
            snapshot(a,zs,cnt,ox,oy,width,height,floor)
            return False
        snapshot(a,zs,cnt,ox,oy,width,height,floor)
        if not move(ds[way]):
            return False
        snapshot(a,zs,cnt,ox,oy,width,height,floor)
        if (get_ground_type() != Grounds.Mushroom
            or measure() != kind or get_pos_z() != z):
            return True
    return False

def tile(arg,size):
    ox, oy, width, height, depth, window = arg
    floor = depth - window
    a = []
    zs = []
    cnt = [0,0,0,0,0,0]
    for cell in range(width * height):
        a.append(-1)
        zs.append(0)
    for y in range(height):
        for step in range(width):
            x = step
            if y % 2 == 1:
                x = width - 1 - step
            if (get_world_size() != size
                or not go(y * width + x,ox,oy,width,size)):
                return False
            while (get_pos_z() >= depth
                and get_ground_type() != Grounds.Mushroom):
                if not dig_one():
                    return False
            snapshot(a,zs,cnt,ox,oy,width,height,floor)
    used = set()
    for attempt in range(width * height * 3):
        if get_world_size() != size:
            return False
        px = get_pos_x() - ox
        py = get_pos_y() - oy
        source = -1
        near = width + height + 1
        for cell in range(len(a)):
            kind = a[cell]
            if kind < 0 or cnt[kind] < 2:
                continue
            dis = abs(cell % width - px) + abs(cell // width - py)
            if dis < near:
                source = cell
                near = dis
        if source < 0:
            return True
        kind = a[source]
        target = -1
        near = width + height + 1
        for cell in range(len(a)):
            if (cell == source or a[cell] != kind
                or (source,cell,kind,zs[source],zs[cell]) in used):
                continue
            dis = abs(cell % width - source % width) + abs(
                cell // width - source // width)
            if dis < near:
                target = cell
                near = dis
        if target < 0:
            remember(a,zs,cnt,source,-1,zs[source])
            continue
        used.add((source,target,kind,zs[source],zs[target]))
        match(source,target,a,zs,cnt,ox,oy,width,height,floor,size)
    return True

def mushroom_job(job):
    if tile(job, get_world_size()):
        return 1
    return 0


def mushroom_round(workers):
    size = get_world_size()
    if size < 2 or not seek_mushroom(size):
        return 0
    depth = get_pos_z()
    jobs = []
    for y in range(0, size, 8):
        for x in range(0, size, 4):
            jobs.append((x, y, min(4, size - x), min(8, size - y), depth, 4))
    before = num_items(Items.Mushroom)
    run_jobs(mushroom_job, jobs, workers)
    return num_items(Items.Mushroom) - before




def adjacent(x, y, direction, n):
    if direction == North:
        return (x, (y + 1) % n)
    if direction == East:
        return ((x + 1) % n, y)
    if direction == South:
        return (x, (y - 1) % n)
    return ((x - 1) % n, y)


def visible_ore(ore):
    if get_ground_type() == ore:
        return True
    for direction in directions():
        if get_ground_type(direction) == ore:
            if move(direction) and get_ground_type() == ore:
                return True
    return False


def queue_ore_neighbors(ore, floor, todo, seen, n):
    x = get_pos_x()
    y = get_pos_y()
    for direction in directions():
        if get_ground_type(direction) == ore:
            z = get_pos_z(direction)
            if z >= floor:
                nx, ny = adjacent(x, y, direction, n)
                key = (nx, ny, z)
                if key not in seen:
                    seen.add(key)
                    todo.append(key)


def drain_vein(ore, floor):
    n = get_world_size()
    x = get_pos_x()
    y = get_pos_y()
    z = get_pos_z()
    first = (x, y, z)
    todo = [first]
    seen = {first}
    total = 0
    while len(todo) > 0:
        x, y, z = todo.pop()
        if go_to(x, y) and get_pos_z() >= floor and get_ground_type() == ore:
            while get_pos_z() >= floor and get_ground_type() == ore:
                queue_ore_neighbors(ore, floor, todo, seen, n)
                if not dig_one():
                    break
                total += 1
                queue_ore_neighbors(ore, floor, todo, seen, n)
    return total


def is_below_ore(ore, ground):
    if ore == Grounds.Petrified_Pumpkin:
        return ground == Grounds.Bedrock
    if (ground == Grounds.Bedrock
        or ground == Grounds.Basalt or ground == Grounds.Dynamite
        or ground == Grounds.Soot or ground == Grounds.Mushroom
        or ground == Grounds.Sand or ground == Grounds.Limestone
        or ground == Grounds.Treasure_Map or ground == Grounds.Treasure_Path
        or ground == Grounds.Treasure_Goal):
        return True
    if ore == Grounds.Coal:
        return (ground == Grounds.Clay or ground == Grounds.Rock
            or ground == Grounds.Iron or ground == Grounds.Quartz
            or ground == Grounds.Petrified_Pumpkin)
    if ore == Grounds.Iron:
        return ground == Grounds.Quartz or ground == Grounds.Petrified_Pumpkin
    return False


def drill_for(ore, floor):
    while get_pos_z() >= floor:
        if visible_ore(ore):
            return drain_vein(ore, floor)
        if is_below_ore(ore, get_ground_type()) or not dig_one():
            break
    return 0


def block_row(row, floor):
    n = get_world_size()
    total = 0
    start = row % 2
    if not go_to(start, row):
        return 0
    for x in range(start, n, 2):
        if not go_to(x, row):
            break
        while get_pos_z() > floor:
            if not dig_one():
                break
            total += 1
    return total


def blocks_round(workers):
    rows = []
    for row in range(get_world_size()):
        rows.append(row)
    depth = 2
    if worker_count(workers, len(rows)) == 1:
        depth = 4
    return run_rows(block_row, rows, workers, (get_pos_z() - depth,))


def ore_row(row, ore, spacing, floor):
    n = get_world_size()
    start = row % spacing
    total = 0
    for x in range(start, n, spacing):
        if go_to(x, row):
            total += drill_for(ore, floor)
    return total


def scan_ore(ore, workers, spacing, stride, depth):
    rows = []
    n = get_world_size()
    for row in range(get_pos_y() % stride, n, stride):
        rows.append(row)
    return (run_rows(ore_row,
        rows, workers, (ore, spacing, get_pos_z() - depth)))


# Depth markers follow the MIT-licensed coal routine in LICENSE-MIT.txt.
def coal_band(job):
    low, high, top, n = job
    for layer in range(16):
        z = top - layer
        start_x = 0
        start_y = low
        forward = East
        next_row = North
        if layer % 2 == 1:
            start_x = n - 1
            start_y = high - 1
            forward = West
            next_row = South
        if not go_to(start_x, start_y):
            return 0
        for row in range(high - low):
            # The end of the preceding pass is the start of this pass.
            deadline = get_time() + 30
            while get_pos_z(North) > z or get_pos_z(South) > z:
                if get_time() >= deadline:
                    return 0
            for col in range(n):
                if get_pos_z() > z or (get_pos_z() == z and not dig_one()):
                    return 0
                if col + 1 < n and not move(forward):
                    return 0
            if row + 1 < high - low:
                if not move(forward) or not move(next_row):
                    return 0
    return 1


def coal_round(workers):
    n = get_world_size()
    count = worker_count(workers, n)
    top = get_pos_z()
    jobs = []
    before = num_items(Items.Coal)
    for rank in range(count):
        jobs.append((rank * n // count, (rank + 1) * n // count, top, n))
    run_jobs(coal_band, jobs, workers)
    return num_items(Items.Coal) - before


def scout_iron(job):
    x, y, budget = job
    if not go_to(x, y):
        return 0
    ore = Grounds.Iron
    n = get_world_size()
    floor = get_pos_z() - 42
    total = 0
    dig_left = 0
    for step in range(n * 2 + 32):
        if visible_ore(ore):
            total += drain_vein(ore, floor)
            dig_left = 0
            continue
        ground = get_ground_type()
        if get_pos_z() < floor or is_below_ore(ore, ground):
            break
        if (ground == Grounds.Rock
            and dig_left == 0 and budget > 0 and num_items(Items.Coal) > 0):
            budget -= 1
            direction = prospect_iron()
            if direction != None:
                if not move(direction):
                    break
                continue
            dig_left = 5
        if dig_left > 0:
            dig_left -= 1
        if not dig_one():
            break
    return total


def prospect_jobs(stock, reserve_per_scout, cap, workers):
    n = get_world_size()
    count = worker_count(workers,
        min(n * n, max(1, stock // reserve_per_scout)))
    columns = 1
    while columns * columns < count:
        columns += 1
    rows = (count + columns - 1) // columns
    jobs = []
    for rank in range(count):
        jobs.append(((rank % columns) * n // columns,
            (rank // columns) * n // rows, min(cap, stock // count)))
    return jobs


def iron_round(workers):
    total = 0
    coal = num_items(Items.Coal)
    if num_unlocked(Unlocks.Prospecting) and coal >= 4:
        jobs = prospect_jobs(coal, 4, 24, workers)
        total = run_jobs(scout_iron, jobs, workers)
    if total == 0:
        total = scan_ore(Grounds.Iron, workers, 5, 4, 42)
    return total


def level_direction(positive, negative, z, coord, n):
    if coord + 1 < n and get_pos_z(positive) == z and can_move(positive):
        return positive
    if coord > 0 and get_pos_z(negative) == z and can_move(negative):
        return negative
    return None


def quartz_offset(before, after):
    offset = (before * before - after * after + 1) / 2
    closest = (offset + 0.5) // 1
    if offset < 0:
        closest = -((-offset + 0.5) // 1)
    if abs(offset - closest) > 0.02:
        return None
    return closest


def quartz_fix(distance):
    # Three readings at one height cancel the unknown vertical term.
    n = get_world_size()
    x = get_pos_x()
    y = get_pos_y()
    z = get_pos_z()
    horizontal = level_direction(East, West, z, x, n)
    if horizontal == None or not move(horizontal):
        return None
    along_x = prospect_quartz()
    vertical = level_direction(North, South, z, y, n)
    if along_x == None or vertical == None or not move(vertical):
        return None
    along_xy = prospect_quartz()
    if along_xy == None:
        return None

    dx = quartz_offset(distance, along_x)
    dy = quartz_offset(along_x, along_xy)
    if dx == None or dy == None:
        return None
    horizontal_sq = dx * dx + dy * dy
    if (abs(dx) * 2 > n
        or abs(dy) * 2 > n or horizontal_sq > distance * distance + 0.02):
        return None
    if horizontal == West:
        dx = -dx
    if vertical == South:
        dy = -dy
    depth = max(0, distance * distance - horizontal_sq) ** 0.5
    return ((x + dx) % n, (y + dy) % n, depth)


def scout_quartz(job):
    x, y, budget = job
    if not go_to(x, y):
        return 0
    ore = Grounds.Quartz
    total = 0
    floor = get_pos_z() - 65
    missed = 0
    for i in range(32):
        if visible_ore(ore):
            total += drain_vein(ore, floor)
            missed = 0
            continue
        if get_pos_z() < floor or is_below_ore(ore, get_ground_type()):
            break
        missed += 1
        if total > 0 and missed >= 5:
            break
        distance = None
        if (budget >= 3 and num_items(Items.Iron) >= 3
            and (get_ground_type() == Grounds.Rock or get_hardness() >= 3)):
            budget -= 3
            distance = prospect_quartz()
        if distance == None or distance <= 1:
            if not dig_one():
                break
        else:
            start_z = get_pos_z()
            fix = quartz_fix(distance)
            if fix != None and go_to(fix[0], fix[1]):
                found = drill_for(ore,
                    max(floor, start_z - (fix[2] // 1) - 2))
                total += found
                if found > 0:
                    missed = 0
            elif not dig_one():
                break
    return total


def quartz_round(workers):
    total = 0
    stock = num_items(Items.Iron)
    if stock >= 3:
        jobs = prospect_jobs(stock, 12, 18, workers)
        total = run_jobs(scout_quartz, jobs, workers)
    if total == 0:
        total = scan_ore(Grounds.Quartz, workers, 4, 3, 65)
    return total


def pumpkin_round(workers):
    return scan_ore(Grounds.Petrified_Pumpkin, workers, 3, 3, 160)




def treasure_round():
    if not seek(Grounds.Basalt, 256):
        return False
    location = measure()
    if location == None or not go_to(location[0], location[1]):
        return False
    if not seek(Grounds.Treasure_Map, 5):
        return False
    path = measure()
    if path == None or len(path) == 0:
        return False
    if path[0] != "D" and not dig_one():
        return False
    directions = {"N": North, "E": East, "S": South, "W": West}
    for step in path:
        if step == "D":
            if not dig_one():
                return False
        elif step not in directions or not move(directions[step]):
            return False
    return get_entity_type() == Entities.Underground_Treasure and harvest()


def pyramid_expose(minimum_z):
    ground = get_ground_type()
    while get_pos_z() > minimum_z:
        if ground == Grounds.Sand or ground == Grounds.Limestone:
            break
        if not dig_one():
            break
        ground = get_ground_type()
    return ground


def pyramid_find(size):
    # A stride of five intersects every generated foundation on this version.
    start_x = get_pos_x()
    start_y = get_pos_y()
    z = get_pos_z()
    for band in range(128):
        z -= 4
        blocked = True
        for dy in range(0, size, 5):
            for step in range(0, size, 5):
                dx = step
                if (dy // 5) % 2 == 1:
                    dx = (size - 1) // 5 * 5 - step
                if not go_to((start_x + dx) % size, (start_y + dy) % size):
                    continue
                ground = pyramid_expose(z)
                if ground == Grounds.Sand or ground == Grounds.Limestone:
                    return True
                if get_pos_z() <= z:
                    blocked = False
        if blocked:
            return False
    return False


def pyramid_find_base(size):
    # A known sand column is inside the foundation. Searching other columns
    # below the foundation can cause its boundary blocks to cave in.
    for step in range(size // 2 + 2):
        ground = get_ground_type()
        if ground == Grounds.Limestone:
            return True
        if ground != Grounds.Sand or not dig_one():
            break
    return get_ground_type() == Grounds.Limestone


def pyramid_on_base(x, y, z, size):
    if not go_to(x % size, y % size):
        return False
    ground = pyramid_expose(z)
    if ground == Grounds.Sand:
        return get_pos_z() > z
    return ground == Grounds.Limestone and get_pos_z() == z


def pyramid_extent(x, y, z, size, dx, dy):
    forward = 0
    for offset in range(1, size):
        if not pyramid_on_base(x + offset * dx, y + offset * dy, z, size):
            break
        forward = offset
    backward = 0
    for offset in range(1, size - forward):
        if not pyramid_on_base(x - offset * dx, y - offset * dy, z, size):
            break
        backward = offset
    return backward, backward + forward + 1


def pyramid_support(z):
    while get_pos_z() < z - 1:
        old_z = get_pos_z()
        if not place(Grounds.Rock) or get_pos_z() <= old_z:
            return False
    if get_pos_z() == z - 1:
        if not place(Grounds.Limestone):
            return False
    return get_pos_z() >= z


def pyramid_round():
    size = get_world_size()
    if not pyramid_find(size) or not pyramid_find_base(size):
        return False
    x = get_pos_x()
    y = get_pos_y()
    z = get_pos_z()
    left, width = pyramid_extent(x, y, z, size, 1, 0)
    bottom, length = pyramid_extent(x, y, z, size, 0, 1)
    if width != length or width % 2 == 0:
        return False
    start_x = x - left
    start_y = y - bottom
    if width == size:
        start_x = 0
        start_y = 0
    center_x = (start_x + width // 2) % size
    center_y = (start_y + width // 2) % size
    if not go_to(center_x, center_y):
        return False
    tip_z = z + width // 2 + 1
    pyramid_expose(z)
    while get_pos_z() >= tip_z:
        if get_ground_type() != Grounds.Sand or not dig_one():
            return False

    # Finish excavation before placing any new sand. A column's height can
    # still change during excavation of adjacent columns.
    for dy in range(width):
        for step in range(width):
            dx = step
            if dy % 2 == 1:
                dx = width - 1 - step
            if not go_to((start_x + dx) % size, (start_y + dy) % size):
                return False
            pyramid_expose(z)
            column_top = z + 1 + min(dx, dy, width - 1 - dx, width - 1 - dy)
            while get_pos_z() > column_top:
                if not dig_one():
                    return False

    for layer in range(width // 2 + 1):
        support_z = z + layer
        for dy in range(layer, width - layer):
            for step in range(layer, width - layer):
                dx = step
                if (dy - layer) % 2 == 1:
                    dx = width - 1 - step
                if not go_to((start_x + dx) % size, (start_y + dy) % size):
                    return False
                if get_pos_z() < z and not pyramid_support(z):
                    return False
                while get_pos_z() <= support_z:
                    old_z = get_pos_z()
                    ground = get_ground_type()
                    if ((old_z == z and ground != Grounds.Limestone)
                        or (old_z > z and ground != Grounds.Sand)):
                        return False
                    if not place(Grounds.Sand):
                        return False
                    if get_entity_type() == Entities.Sunflower:
                        return pyramid_harvest()
                    if get_pos_z() <= old_z:
                        return False
    return go_to(center_x, center_y) and pyramid_harvest()


def pyramid_harvest():
    deadline = get_time() + 10
    while get_entity_type() == Entities.Sunflower:
        if can_harvest():
            return harvest()
        if get_time() > deadline:
            break
    return False


def sweeper_neighbors(tile, size):
    neighbors = []
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            x = tile[0] + dx
            y = tile[1] + dy
            if ((dx != 0
                or dy != 0) and x >= 0 and x < size and y >= 0 and y < size):
                neighbors.append((x, y))
    return neighbors


def sweeper_equation(tile, size, state, clues):
    remaining = clues[tile]
    unknown = set()
    for neighbor in sweeper_neighbors(tile, size):
        if neighbor not in state:
            unknown.add(neighbor)
        elif state[neighbor] == 1:
            remaining -= 1
    return unknown, remaining


def sweeper_mark(tile, value, size, state, safe, clues, dirty):
    state[tile] = value
    if value == 0:
        safe.add(tile)
    for neighbor in sweeper_neighbors(tile, size):
        if neighbor in clues:
            dirty.add(neighbor)


def sweeper_direct(size, state, safe, clues, dirty):
    while len(dirty) > 0:
        checking = []
        for tile in dirty:
            checking.append(tile)
        for tile in checking:
            dirty.remove(tile)
            unknown, count = sweeper_equation(tile, size, state, clues)
            if count == 0 or count == len(unknown):
                value = 0
                if count > 0:
                    value = 1
                for neighbor in unknown:
                    sweeper_mark(neighbor,
                        value, size, state, safe, clues, dirty)


def sweeper_mark_group(tiles, low, high, size, state, safe, clues, dirty):
    if len(tiles) == 0 or (high != 0 and low != len(tiles)):
        return False
    value = 0
    if low > 0:
        value = 1
    for tile in tiles:
        sweeper_mark(tile, value, size, state, safe, clues, dirty)
    return True


def sweeper_overlap(size, state, safe, clues, dirty):
    # Bound the mines in the intersection, then in each disjoint remainder.
    frontier = {}
    for tile in clues:
        unknown, count = sweeper_equation(tile, size, state, clues)
        if 0 < count and count < len(unknown):
            frontier[tile] = (unknown, count)
    for tile in frontier:
        first, first_count = frontier[tile]
        for dy in range(3):
            for dx in range(-2, 3):
                if dy == 0 and dx <= 0:
                    continue
                other = (tile[0] + dx, tile[1] + dy)
                if other not in frontier:
                    continue
                second, second_count = frontier[other]
                common = []
                first_only = []
                second_only = []
                for neighbor in first:
                    if neighbor in second:
                        common.append(neighbor)
                    else:
                        first_only.append(neighbor)
                if len(common) == 0:
                    continue
                for neighbor in second:
                    if neighbor not in first:
                        second_only.append(neighbor)
                low = max(0, first_count - len(first_only),
                    second_count - len(second_only))
                high = min(len(common), first_count, second_count)
                if low > high:
                    continue
                common_marked = sweeper_mark_group(common,
                    low, high, size, state, safe, clues, dirty)
                first_marked = sweeper_mark_group(first_only,
                    first_count - high,
                    first_count - low, size, state, safe, clues, dirty)
                second_marked = sweeper_mark_group(second_only,
                    second_count - high,
                    second_count - low, size, state, safe, clues, dirty)
                if common_marked or first_marked or second_marked:
                    return True
    return False


def sweeper_distance(tile, x, y, size):
    dx = abs(tile[0] - x)
    dy = abs(tile[1] - y)
    return min(dx, size - dx) + min(dy, size - dy)


def sweeper_choose(size, state, safe, clues):
    x = get_pos_x()
    y = get_pos_y()
    closest = None
    distance = size + 1
    for tile in safe:
        steps = sweeper_distance(tile, x, y, size)
        if steps < distance:
            closest = tile
            distance = steps
            if steps <= 1:
                break
    if closest != None:
        return closest

    # Use the lowest local mine estimate only after exhausting provably safe
    # tiles.
    risks = {}
    for tile in clues:
        unknown, count = sweeper_equation(tile, size, state, clues)
        if len(unknown) > 0:
            risk = count / len(unknown)
            for candidate in unknown:
                if candidate not in risks or risks[candidate] < risk:
                    risks[candidate] = risk
    best_risk = 2
    for tile in risks:
        steps = sweeper_distance(tile, x, y, size)
        if (risks[tile] < best_risk
            or (risks[tile] == best_risk and steps < distance)):
            closest = tile
            distance = steps
            best_risk = risks[tile]
    if closest != None and best_risk <= 0.18:
        return closest
    # An unconstrained tile can be safer than a tight local frontier.
    unknown_tile = None
    unknown_distance = size + 1
    for dy in range(size):
        for dx in range(size):
            tile = ((x + dx) % size, (y + dy) % size)
            if tile not in state and tile not in risks:
                steps = sweeper_distance(tile, x, y, size)
                if steps < unknown_distance:
                    unknown_tile = tile
                    unknown_distance = steps
                    if steps <= 1:
                        return tile
    if unknown_tile != None:
        return unknown_tile
    return closest


def sweeper_open(tile, dynamite_z):
    if not go_to(tile[0], tile[1]):
        return False
    while get_pos_z() > dynamite_z:
        if get_ground_type() == Grounds.Dynamite or not dig_one():
            return False
    if get_pos_z() == dynamite_z:
        if get_ground_type() != Grounds.Dynamite or not dig_one():
            return False
    if get_pos_z() != dynamite_z - 1 or get_ground_type() != Grounds.Soot:
        return False
    if get_entity_type() == Entities.Dynamite:
        harvest()
    return True


def sweeper_record(tile, count, size, state, safe, clues, dirty):
    if tile in safe:
        safe.remove(tile)
    clues[tile] = count
    dirty.add(tile)
    sweeper_mark(tile, 2, size, state, safe, clues, dirty)


def dynamite_round():
    if not seek(Grounds.Dynamite, 128):
        return False
    size = get_world_size()
    z = get_pos_z()
    state = {}
    safe = set()
    clues = {}
    dirty = set()
    x = get_pos_x()
    y = get_pos_y()
    if size > 3:
        x = min(max(1, x), size - 2)
        y = min(max(1, y), size - 2)
    tile = (x, y)
    adjacent = ((North, 0, 1), (East, 1, 0), (South, 0, -1), (West, -1, 0))
    for step in range(size * size):
        if not sweeper_open(tile, z):
            return False
        count = measure()
        if count == None:
            return True
        sweeper_record(tile, count, size, state, safe, clues, dirty)
        for direction, dx, dy in adjacent:
            x = tile[0] + dx
            y = tile[1] + dy
            neighbor = (x, y)
            if (0 <= x and x < size
                and 0 <= y and y < size and neighbor not in clues):
                if (get_pos_z(direction) == z - 1
                    and get_ground_type(direction) == Grounds.Soot):
                    count = measure(direction)
                    if count != None:
                        sweeper_record(neighbor,
                            count, size, state, safe, clues, dirty)
        sweeper_direct(size, state, safe, clues, dirty)
        while (len(safe) == 0
            and sweeper_overlap(size, state, safe, clues, dirty)):
            sweeper_direct(size, state, safe, clues, dirty)
        tile = sweeper_choose(size, state, safe, clues)
        if tile == None:
            # Zero clues can uncover duds automatically. Once every mine is
            # known
            # and all duds are open, dig the exposed soot to cash in the full
            # score.
            return dig()
    return False


def mining_map_size(mode):
    if mode == "coal":
        return 12
    if mode == "quartz":
        return 28
    if mode == "pyramid_power":
        return 24
    return 32


def run_mining(mode, rounds, workers, map_size=0):
    modes = {
        "block": (Unlocks.Mining, Items.Block),
        "coal": (Unlocks.Coal, Items.Coal),
        "rice": (Unlocks.Rice, Items.Rice),
        "iron": (Unlocks.Iron, Items.Iron),
        "quartz": (Unlocks.Quartz, Items.Quartz),
        "bamboo": (Unlocks.Bamboo, Items.Bamboo),
        "bamboo_perlite": (Unlocks.Bamboo, Items.Bamboo),
        "mushroom": (Unlocks.Mushrooms, Items.Mushroom),
        "dynamite": (Unlocks.Dynamite, Items.Dynamite),
        "petrified_pumpkin": (Unlocks.Petrified_Pumpkins, Items.Pumpkin),
        "treasure_gold": (Unlocks.Treasure_Map, Items.Gold),
        "pyramid_power": (Unlocks.Pyramid, Items.Power),
    }
    if (mode not in modes or rounds < 1 or workers < 0
        or map_size < -1 or map_size == 1 or map_size == 2 or map_size > 32):
        quick_print("Invalid mining MODE, ROUNDS, WORKERS or MAP_SIZE.")
        return 0

    unlock, item = modes[mode]
    if (not num_unlocked(Unlocks.Mining) or not num_unlocked(
        Unlocks.Underground_Senses) or not num_unlocked(unlock)):
        quick_print("Mining mode is locked:",
            mode, "needs Mining, Underground Senses and", unlock)
        return 0
    if mode == "bamboo_perlite" and not num_unlocked(Unlocks.Special_Soils):
        quick_print("Bamboo on perlite needs Special Soils.")
        return 0

    before = num_items(item)
    start = get_time()
    if map_size == -1:
        map_size = mining_map_size(mode)
    if (map_size > 0
        and num_unlocked(Unlocks.Debug_2) and map_size != get_world_size()):
        set_world_size(map_size)
    clear()
    if mode == "bamboo":
        bamboo_run(rounds, workers)
    elif mode == "bamboo_perlite":
        bamboo_perlite_run(rounds, workers)
    else:
        if mode != "block" and mode != "coal" and num_unlocked(Unlocks.Jump):
            jump(unlock)
        for r in range(rounds):
            if r > 0:
                clear()
            if mode == "block":
                blocks_round(workers)
            elif mode == "coal":
                coal_round(workers)
            elif mode == "rice":
                rice_round(workers)
            elif mode == "iron":
                iron_round(workers)
            elif mode == "quartz":
                quartz_round(workers)
            elif mode == "mushroom":
                mushroom_round(workers)
            elif mode == "dynamite":
                dynamite_round()
            elif mode == "petrified_pumpkin":
                pumpkin_round(workers)
            elif mode == "treasure_gold":
                treasure_round()
            elif mode == "pyramid_power":
                pyramid_round()
    gain = num_items(item) - before
    elapsed = get_time() - start
    if elapsed > 0:
        quick_print(mode, "net gain:",
            gain, "seconds:", elapsed, "items/min:", gain * 60 / elapsed)
    return gain
