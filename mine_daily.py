from mine_core import run_mining

# See the mine_get_* windows for a one-click launcher per resource.
MODE = "coal"
ROUNDS = 1
WORKERS = 0   # 0 uses all available drones.
MAP_SIZE = -1  # -1 uses the tested size. 0 keeps the current size.

run_mining(MODE, ROUNDS, WORKERS, MAP_SIZE)
