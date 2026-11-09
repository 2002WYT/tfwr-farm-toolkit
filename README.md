# The Farmer Was Replaced Toolkit

Harvesting, leaderboard, and benchmarking scripts for [The Farmer Was Replaced](https://store.steampowered.com/app/2060160/The_Farmer_Was_Replaced/). The daily script collects crops, power, gold, bones, and Weird Substance. During testing, the scripts reached the Steam global top 100 in all 15 base-game resource leaderboards. See the [results and reproduction steps](docs/benchmarks.md).

## Installation

1. In the game menu, select **Load → Open Folder** to locate the save directory. Save the current game and back up that directory.
2. Let the current harvest finish or stop it, then copy all `farm_*.py` files from the repository root into the save directory. Keep the game's `__builtins__.py` and save files in place.
3. Reload the save. Daily scripts use the save's current research levels and inventory. Leaderboard runs and simulations require their corresponding unlocks.

Run these scripts in the in-game interpreter. The entry points import helper modules from the same directory.

## Entry points

| Task | Settings to edit | Window to run |
|---|---|---|
| Daily harvesting | `MODE` and `ROUNDS` in `farm_run` | `farm_run` |
| Official leaderboard run | `CATEGORY` and `SINGLE_DRONE` in `farm_rank_core` | `farm_rank` |
| Fixed-seed benchmark | `CASES` in `farm_rank_lab` | `farm_rank_lab` |
| Regression checks | `SUITE` in `farm_test` | `farm_test` |

The repository defaults to `ROUNDS = 1` so you can try one round before increasing it. `WORKERS = 0` uses all available drones. `WATER_BELOW = 0` disables watering. When the field or inventory is unsuitable, the daily script either uses a fallback route or stops before planting and prints the reason. For leaderboard runs, `VARIANT = -1` selects the validated variant. Set `SINGLE_DRONE = False` for the dinosaur leaderboard. The game submits official scores to Steam.

In the game, keep `farm_run`, `farm_rank_core`, and `farm_rank` open for easy access. Use the minimize button to collapse helper windows. Comments next to each setting explain what it controls.

## Algorithms and attribution

- `farm_rank_hay_reference.py` ports enihsyou's single-drone and multi-drone hay routes into callable functions.
- `farm_bone_rail.py` adapts the same project's dinosaur perimeter route. This project adds final-apple handling and the variant 8 perimeter optimization.
- This project implements the other leaderboard routes, daily adapters, and tests. The [algorithm guide](docs/algorithms.md) explains their prerequisites and credits the public strategies that informed them.

Both upstream-derived modules retain the original copyright notice and MIT license. See the [third-party notices](THIRD_PARTY_NOTICES.md).
