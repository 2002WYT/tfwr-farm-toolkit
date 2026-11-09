# Source https://github.com/enihsyou/The-Farmer-Was-Replaced/blob/main/dianosaus.py
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

def harvest_dianosaus():
    change_hat(Hats.Dinosaur_Hat)
    cycle_loop()
    change_hat(Hats.Brown_Hat)


def _known_rim(direction, x, y, last_row, apple_x, apple_y):
    # Stay on the perimeter. If the known apple is ahead, end the segment on its tile.
    if direction == North:
        steps = last_row - y
        if x == apple_x and apple_y > y:
            steps = apple_y - y
    else:
        steps = y
        if x == apple_x and apple_y < y:
            steps = y - apple_y
    for step in range(steps):
        if not move(direction):
            break


def cycle_loop(safety=0):
    # Implementation reference
    # https://www.reddit.com/r/TheFarmerWasReplaced/comments/1o90hxs/my_sna_i_mean_dinosaur_algorithm/
    s = get_world_size()
    m = s - 1
    l = s * s // 2  # Use the Hamiltonian-style sweep once the tail passes this length.

    dir = East
    snake = 0
    known = False
    while True:
        x, y = get_pos_x(), get_pos_y()
        if get_entity_type() == Entities.Apple:
            snake += 1
            prediction = measure()
            if safety > 0 and (snake == s * s - 1 or prediction == None):
                # Finish the last growth by moving off the apple in a legal direction.
                for direction in [North, East, South, West]:
                    if move(direction):
                        return
                return
            wx, wy = prediction
            known = safety == 3

        # Fill open space to favor apples ahead of the snake. The upstream author measured about a 10% speedup.
        if snake > l:
            if y == 0 and can_move(North) and x % 2 == 1:
                steps = m - 1
                if safety == 1 and x == wx and 0 < wy < m:
                    # Stop on the apple so the next measurement updates the target.
                    steps = wy
                if known and x == wx and 0 < wy and wy <= steps:
                    # Keep the full sweep. If it crosses an apple, check tiles until the next measurement.
                    known = False
                for _ in range(steps):  # Leave the northernmost row for the return path.
                    # Crossing an apple here can trap the snake. The upstream author measured about a 10% gain from skipping checks.
                    move(North)
                continue

        # Reach apples in the interior.
        if x != 0 and x != m:  # Skip the west and east edges.
            if (x == wx or x + 1 == wx) and x % 2 == 1:
                if can_move(North) and wy > y and wy != m:  # Check whether a northbound move can reach the apple.
                    for _ in range(wy - y):
                        move(North)
                    continue
            if (x == wx or x - 1 == wx) and x % 2 == 0:
                if can_move(South) and y > wy and wy != 0:  # Check whether a southbound move can reach the apple.
                    for _ in range(y - wy):
                        move(South)
                    continue

        # Follow the perimeter counterclockwise.
        if dir == East:
            if y != 0 and can_move(South):
                if known:
                    _known_rim(South, x, y, m, wx, wy)
                else:
                    while move(South) and get_entity_type() != Entities.Apple:
                        continue  # Return to the perimeter.
                continue
            if x == m:
                dir = North  # Turn north at the boundary and move immediately to save an iteration.
            if not (move(dir) or move(North)):  # Try the direction with space when the boundary or tail blocks the route.
                break
            continue
        if dir == West:
            if y == m and can_move(dir) and x > wx + 1:
                for _ in range(x - wx - 1 - 1):  # Leave one extra column for parity.
                    move(dir)  # Traverse the north edge quickly on the return leg.
            if y != m and can_move(North):
                if known:
                    _known_rim(North, x, y, m, wx, wy)
                else:
                    while move(North) and get_entity_type() != Entities.Apple:
                        continue  # Return to the perimeter.
                continue
            if x == 0:
                dir = South  # Turn south at the boundary.
            if not (move(dir) or move(South)):  # Try the direction with space when the boundary or tail blocks the route.
                break
            continue
        if dir == South:
            if x != 0 and can_move(West):
                move(West)  # Return to the perimeter.
                continue
            if x == 0 and y != 0:
                if known:
                    _known_rim(South, x, y, m, wx, wy)
                else:
                    while move(dir) and get_entity_type() != Entities.Apple:
                        continue  # Traverse a straight edge segment inside this loop.
                if not (can_move(dir) or can_move(East)):
                    break  # The tail blocks the perimeter.
            dir = East  # Turn east at the boundary.
            continue
        if dir == North:
            if x != m and can_move(East):
                move(East)  # Return to the perimeter.
                continue
            if x == m and y != m:
                if known:
                    _known_rim(North, x, y, m, wx, wy)
                else:
                    while move(dir) and get_entity_type() != Entities.Apple:
                        continue  # Traverse a straight edge segment inside this loop.
                if not can_move(dir) and not can_move(West):
                    break  # The tail blocks the perimeter.
            dir = West  # Turn west at the boundary.
            continue


if __name__ == "__main__":
    # set_world_size(8)
    # b = num_items(Items.Bone)
    harvest_dianosaus()
    # a = num_items(Items.Bone)
    # h = a - b
    # quick_print("Harvest Bones", h, "is Done?", h >= 33488928)
