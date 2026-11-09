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
    # 仍在同一段边线上走。已知苹果在前方时，直接把步数截到苹果格。
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
    # 参照这个地址来实现
    # https://www.reddit.com/r/TheFarmerWasReplaced/comments/1o90hxs/my_sna_i_mean_dinosaur_algorithm/
    s = get_world_size()
    m = s - 1
    l = s * s // 2  # 大于这个长度就强制走汉密顿路径

    dir = East
    snake = 0
    known = False
    while True:
        x, y = get_pos_x(), get_pos_y()
        if get_entity_type() == Entities.Apple:
            snake += 1
            prediction = measure()
            if safety > 0 and (snake == s * s - 1 or prediction == None):
                # 最后一次增长只需要离开苹果。先用实际规则确认有路可走。
                for direction in [North, East, South, West]:
                    if move(direction):
                        return
                return
            wx, wy = prediction
            known = safety == 3

        # 不留缝隙地占满空间，强迫果子生成在前方，提速 10%
        if snake > l:
            if y == 0 and can_move(North) and x % 2 == 1:
                steps = m - 1
                if safety == 1 and x == wx and 0 < wy < m:
                    # 确保下一次测量发生在苹果格，避免直走时跳过更新。
                    steps = wy
                if known and x == wx and 0 < wy and wy <= steps:
                    # 保留完整波形。中途若经过苹果，直到下一次测量前逐格检查。
                    known = False
                for _ in range(steps):  # 避开最北的一行
                    # 如果不幸在这里吃到果子，会卡死，但是省略判断能提速 10%
                    move(North)
                continue

        # 访问中心区域的果子
        if x != 0 and x != m:  # 不在左右两侧
            if (x == wx or x + 1 == wx) and x % 2 == 1:
                if can_move(North) and wy > y and wy != m:  # 向北可以到达苹果
                    for _ in range(wy - y):
                        move(North)
                    continue
            if (x == wx or x - 1 == wx) and x % 2 == 0:
                if can_move(South) and y > wy and wy != 0:  # 向南可以前往苹果
                    for _ in range(y - wy):
                        move(South)
                    continue

        # 围着操场逆时针转圈
        if dir == East:
            if y != 0 and can_move(South):
                if known:
                    _known_rim(South, x, y, m, wx, wy)
                else:
                    while move(South) and get_entity_type() != Entities.Apple:
                        continue  # 回归边线
                continue
            if x == m:
                dir = North  # 在边界转向, 下面直接 move 节约一个循环
            if not (move(dir) or move(North)):  # 碰到边界或尾巴，向有空间的方向前进
                break
            continue
        if dir == West:
            if y == m and can_move(dir) and x > wx + 1:
                for _ in range(x - wx - 1 - 1):  # 考虑到奇偶性，多减 1
                    move(dir)  # 快速移过最北边, 因为那是回程的线
            if y != m and can_move(North):
                if known:
                    _known_rim(North, x, y, m, wx, wy)
                else:
                    while move(North) and get_entity_type() != Entities.Apple:
                        continue  # 回归边线
                continue
            if x == 0:
                dir = South  # 在边界转向
            if not (move(dir) or move(South)):  # 碰到边界或尾巴，向有空间的方向前进
                break
            continue
        if dir == South:
            if x != 0 and can_move(West):
                move(West)  # 回归边线
                continue
            if x == 0 and y != 0:
                if known:
                    _known_rim(South, x, y, m, wx, wy)
                else:
                    while move(dir) and get_entity_type() != Entities.Apple:
                        continue  # 边界上走直线，避免循环顶层大 while
                if not (can_move(dir) or can_move(East)):
                    break  # 碰到尾巴
            dir = East  # 在边界转向
            continue
        if dir == North:
            if x != m and can_move(East):
                move(East)  # 回归边线
                continue
            if x == m and y != m:
                if known:
                    _known_rim(North, x, y, m, wx, wy)
                else:
                    while move(dir) and get_entity_type() != Entities.Apple:
                        continue  # 边界上走直线，避免循环顶层大 while
                if not can_move(dir) and not can_move(West):
                    break  # 碰到尾巴
            dir = West  # 在边界转向
            continue


if __name__ == "__main__":
    # set_world_size(8)
    # b = num_items(Items.Bone)
    harvest_dianosaus()
    # a = num_items(Items.Bone)
    # h = a - b
    # quick_print("Harvest Bones", h, "is Done?", h >= 33488928)
