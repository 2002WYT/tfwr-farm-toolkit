def move_axis(offset, forward, backward, n):
    # 地表边缘可以绕回，走较短的一侧。
    steps = offset % n
    direction = forward
    if steps * 2 > n:
        steps = n - steps
        direction = backward
    for step in range(steps):
        if not move(direction):
            return False
    return True


def go(x, y, n):
    return (move_axis(x - get_pos_x(), East, West, n)
            and move_axis(y - get_pos_y(), North, South, n))


def parallel(task, n, workers, arg, split=False):
    # 主机处理第一块，子机各管一块。结果按编号返回，下一阶段等全部结束再开始。
    handles = []
    for worker in range(1, workers):
        payload = arg
        if split:
            payload = arg[worker]
        if split and len(payload) == 0:
            handles.append(None)
        else:
            handles.append(spawn_drone(task, worker, n, workers, payload))

    payload = arg
    if split:
        payload = arg[0]
    results = [task(0, n, workers, payload)]
    for index in range(len(handles)):
        drone = handles[index]
        if drone == None:
            worker = index + 1
            payload = arg
            if split:
                payload = arg[worker]
            results.append(task(worker, n, workers, payload))
        else:
            results.append(wait_for(drone))
    return results
