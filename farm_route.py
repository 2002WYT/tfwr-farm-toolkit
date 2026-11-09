def move_axis(offset, forward, backward, n):
    # Surface edges wrap. Take the shorter direction.
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
    # Run one block locally and give each child its own block. Wait for all results before the next phase.
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
