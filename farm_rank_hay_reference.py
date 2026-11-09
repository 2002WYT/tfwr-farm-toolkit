# Sources https://github.com/enihsyou/The-Farmer-Was-Replaced/blob/main/hay.py
# and https://github.com/enihsyou/The-Farmer-Was-Replaced/blob/main/hay_single.py
# MIT License
#
# Copyright (c) 2026 enihsyou
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


def run_multi_hay():
    N = 2000000000
    W = 0.68

    OFFSETS = {
        North: (0, 1),
        South: (0, -1),
        East: (1, 0),
        West: (-1, 0),
    }
    OPPOSITES = {
        North: South,
        South: North,
        East: West,
        West: East,
    }


    def visit_neighbors_creator(dirs):
        visited = set()

        def r(i):
            for d in dirs:
                cx, cy = get_pos_x(), get_pos_y()
                dx, dy = OFFSETS[d]
                nx, ny = cx + dx, cy + dy
                next = (nx, ny)
                if next in visited:
                    continue
                visited.add(next)
                move(d)
                plant(Entities.Bush)
                if i < 3:
                    r(i + 1)
                # backtrack
                move(OPPOSITES[d])

        return r


    VISIT_EAST = visit_neighbors_creator([East, North, South])
    VISIT_WEST = visit_neighbors_creator([West, North, South])
    VISIT_NORTH = visit_neighbors_creator([North])
    VISIT_SOUTH = visit_neighbors_creator([South])


    def plant_bush_around():
        move(West)
        VISIT_WEST(2)
        move(East)

        VISIT_NORTH(1)
        VISIT_SOUTH(1)

        move(East)

        VISIT_NORTH(1)
        VISIT_SOUTH(1)

        move(East)
        VISIT_EAST(2)
        move(West)


    def harvest_poly_hay(avoid_x, avoid_y):
        while get_water() < W and num_items(Items.Water) > 16:
            use_item(Items.Water)
        harvest()
        c, pos = get_companion()
        x, y = pos
        while c != Entities.Bush or (x == avoid_x and y == avoid_y):
            harvest()
            c, pos = get_companion()
            x, y = pos


    def work_drone_task():
        plant_bush_around()
        y = get_pos_y()
        x_east = get_pos_x()
        x_west = x_east - 1
        for _ in range(360):  # 每部无人机预计需要 381 次收集能达到目标
            harvest_poly_hay(x_west, y)
            move(West)
            harvest_poly_hay(x_east, y)
            move(East)
        while True:
            harvest_poly_hay(x_west, y)
            if num_items(Items.Hay) >= N:
                return
            move(West)
            harvest_poly_hay(x_east, y)
            if num_items(Items.Hay) >= N:
                return
            move(East)


    def diagonal_move_do(side_lenth, d1, d2, do):
        def fn():
            for _ in range(side_lenth):
                move(d1)
                move(d2)
            do()

        return fn


    DIRECTIONS = [North, East, South, West]


    def spawn_drone_task1():
        for i in range(len(DIRECTIONS)):
            d1 = DIRECTIONS[i]
            d2 = DIRECTIONS[(i + 1) % len(DIRECTIONS)]
            spawn_drone(diagonal_move_do(8, d1, d2, spawn_drone_task2(i)))
            spawn_drone(diagonal_move_do(4, d1, d1, work_drone_task))
        work_drone_task()


    def spawn_drone_task2(d):
        def fn():
            for i in range(len(DIRECTIONS)):
                d1 = DIRECTIONS[i]
                d2 = DIRECTIONS[(i + 1) % len(DIRECTIONS)]
                spawn_drone(diagonal_move_do(4, d1, d2, spawn_drone_task3(i)))
            work_drone_task()

        return fn


    def spawn_drone_task3(d):
        def fn():
            x, y = get_pos_x(), get_pos_y()
            if x == border[0] or y == border[1]:
                spawn_drone(diagonal_move_do(4, North, East, work_drone_task))
            work_drone_task()

        return fn


    clear()
    # debug purpose: move to center
    # for _ in range(12):
    #     move(North)
    #     move(East)
    center = (get_pos_x(), get_pos_y())
    border = (center[0] + 12, center[1] + 12)
    spawn_drone_task1()


def run_single_hay():
    # 周围三格种上草丛
    set_world_size(5)
    for dir in (
        North,
        North,
        North,
        North,
        # at (0, 4)
        East,
        # at (1, 4)
        South,
        South,
        South,
        # at (1, 1)
        East,
        # at (2, 1)
        North,
        North,
        North,
        North,
        # at (2, 0)
        East,
        North,
        # at (3, 1)
        East,
        North,
        North,
        # at (4, 3)
        West,
        North,
        East,
        # at (4, 4)
        North,
        # at (4, 0)
    ):
        move(dir)
        plant(Entities.Bush)
    move(East)
    # at (0, 0)

    W = 0.68  # 替代 can_harvest() 等待时间的最小值
    A, B = (0, 0), (1, 0)

    # 理想状态下需要 1220 次完整加成的 harvest

    # 第一个循环，补水
    while get_water() < W:
        use_item(Items.Water)
    harvest()  # move 消耗的时间基本抵消了成长时间，无需 can_harvest()
    c, pos = get_companion()
    while c != Entities.Bush or pos == B:
        harvest()
        c, pos = get_companion()
    move(East)

    while get_water() < W:
        use_item(Items.Water)
    harvest()
    c, pos = get_companion()
    while c != Entities.Bush or pos == A:
        harvest()
        c, pos = get_companion()
    move(West)

    # 第二个循环，省略数量判断
    for _ in range(604):
        if get_water() < W:
            use_item(Items.Water)
        harvest()  # move 消耗的时间基本抵消了成长时间，无需 can_harvest()
        c, pos = get_companion()
        while c != Entities.Bush or pos == B:
            harvest()
            c, pos = get_companion()
        move(East)

        if get_water() < W:
            use_item(Items.Water)
        harvest()
        c, pos = get_companion()
        while c != Entities.Bush or pos == A:
            harvest()
            c, pos = get_companion()
        move(West)

    # 第三个循环，省略补水，直到收集足够的干草
    while True:
        harvest()  # move 消耗的时间基本抵消了成长时间，无需 can_harvest()
        if num_items(Items.Hay) > 100000000:
            break
        c, pos = get_companion()
        while c != Entities.Bush or pos == B:
            harvest()
            c, pos = get_companion()
        move(East)

        harvest()
        if num_items(Items.Hay) > 100000000:
            break
        c, pos = get_companion()
        while c != Entities.Bush or pos == A:
            harvest()
            c, pos = get_companion()
        move(West)
