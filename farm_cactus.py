from farm_route import go, parallel


def _sweep(start, end, step, advance, retreat):
    # Negating sizes lets a reverse sweep use the same comparisons.
    position = start
    last_swap = start
    value = measure() * step
    behind = value

    while True:
        ahead = measure(advance) * step
        # Both swaps can run from this tile, saving a move between them.
        while True:
            if value > ahead:
                if not swap(advance):
                    return None
                old_value = value
                value = ahead
                ahead = old_value
                last_swap = position
            elif position != start and behind > value:
                if not swap(retreat):
                    return None
                old_value = value
                value = behind
                behind = old_value
                if last_swap != position:
                    last_swap = position - step
            else:
                break

        # The last comparison is made from one tile short of the far end.
        position += step
        if position == end:
            return last_swap
        if not move(advance):
            return None
        behind = value
        value = ahead


def _go_to_line(stripe, position, n, columns):
    if columns:
        return go(stripe, position, n)
    return go(position, stripe, n)


def _sort_stripes(worker_id, n, workers, columns):
    if columns:
        forward = North
        backward = South
    else:
        forward = East
        backward = West

    for stripe in range(worker_id, n, workers):
        low = 0
        high = n - 1
        # Each sweep settles the end of the line beyond its last swap.
        while low < high:
            if not _go_to_line(stripe, low, n, columns):
                return False
            high = _sweep(low, high, 1, forward, backward)
            if high == None:
                return False
            if low == high:
                break
            if not _go_to_line(stripe, high, n, columns):
                return False
            low = _sweep(high, low, -1, backward, forward)
            if low == None:
                return False
    return True


def sort_and_harvest(n, workers):
    # Sorting columns preserves the ordering already established in the rows.
    for columns in [False, True]:
        for done in parallel(_sort_stripes, n, workers, columns):
            if not done:
                return False
    return harvest()
