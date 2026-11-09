# The Farmer Was Replaced Toolkit

Harvesting, leaderboard, and benchmarking scripts for [The Farmer Was Replaced](https://store.steampowered.com/app/2060160/The_Farmer_Was_Replaced/). Daily launchers collect farm and Mining DLC resources. During testing, the scripts reached the Steam global top 100 in all 15 base-game resource leaderboards. See the [results and reproduction steps](docs/benchmarks.md).

## Installation

1. Select **Load → Open Folder** in the game and back up the save you use.
2. Stop any running script. Copy the repository's root `farm_*.py` files into
   the save directory. For the Mining DLC, copy the root `mine_*.py` files too.
3. Reload the save and open the launcher for the resource you want.

## Run a resource

Open a launcher and press its leftmost **Run** button. You can run it while
the window is minimized. Each launcher uses its existing daily route and
defaults to one round. Edit `ROUNDS` in that launcher for longer runs.

| Area | Launchers |
|---|---|
| Farm crops | `farm_get_hay`, `farm_get_wood`, `farm_get_carrot`, `farm_get_pumpkin`, `farm_get_power`, `farm_get_cactus` |
| Other farm resources | `farm_get_bone`, `farm_get_gold`, `farm_get_substance`, `farm_get_water`, `farm_get_fertilizer` |
| Mining DLC | `mine_get_block`, `mine_get_coal`, `mine_get_rice`, `mine_get_iron`, `mine_get_quartz`, `mine_get_bamboo`, `mine_get_bamboo_perlite`, `mine_get_mushroom`, `mine_get_dynamite`, `mine_get_petrified_pumpkin`, `mine_get_treasure_gold`, `mine_get_pyramid_power` |

Daily launchers clear the current field before collecting. Mining launchers
check the relevant unlocks first. The launchers use the save's own inventory
and research. The water and fertilizer launchers collect passive supplies
for 10 game seconds per round. See the [mining guide](#mining-dlc-routes) for
recommended sizes and routes.

| Task | Settings | Window |
|---|---|---|
| Custom farm collection | `MODE`, `ROUNDS`, `WORKERS`, `WATER_BELOW`, `MIXED` | `farm_run` |
| Custom mining | `MODE`, `ROUNDS`, `WORKERS`, `MAP_SIZE` | `mine_daily` |
| Official leaderboard run | `CATEGORY` and `SINGLE_DRONE` in `farm_rank_core` | `farm_rank` |
| Fixed-seed farm benchmark | `CASES` | `farm_rank_lab` |
| Farm regression checks | `SUITE` | `farm_test` |

`WORKERS = 0` uses all available drones. `WATER_BELOW = 0` disables
watering. For farm leaderboard runs, `VARIANT = -1` selects the validated
variant. Set `SINGLE_DRONE = False` for the dinosaur leaderboard.
The game submits official leaderboard scores to Steam.

## Algorithms and attribution

- `farm_rank_hay_reference.py` ports enihsyou's single-drone and multi-drone hay routes into callable functions.
- `farm_bone_rail.py` adapts the same project's dinosaur perimeter route. This project adds final-apple handling and the variant 8 perimeter optimization.
- This project implements the other leaderboard routes, daily adapters, and tests. The [algorithm guide](docs/algorithms.md) explains their prerequisites and credits the public strategies that informed them.

Both upstream-derived modules retain the original copyright notice and MIT license. See the [third-party notices](THIRD_PARTY_NOTICES.md).

## Mining DLC routes

Run the named `mine_get_*` window for the desired resource. Each launcher
uses all available drones, runs one round, and selects a tested map size.
For custom runs, `mine_daily` uses the same routes. Set `MAP_SIZE = -1` for
the tested size or `0` to keep the current size. Resizing needs Debug 2.

| Resource or route | Launcher suffix | Tested side length |
|---|---|---:|
| Block | `block` | 32 |
| Coal | `coal` | 12 |
| Rice | `rice` | 32 |
| Iron | `iron` | 32 |
| Quartz | `quartz` | 28 |
| Bamboo on the surface | `bamboo` | 32 |
| Bamboo on perlite | `bamboo_perlite` | 32 |
| Mushroom | `mushroom` | 32 |
| Dynamite | `dynamite` | 32 |
| Petrified pumpkin | `petrified_pumpkin` | 32 |
| Treasure-map gold | `treasure_gold` | 32 |
| Pyramid power | `pyramid_power` | 24 |

The runners require Mining, Underground Senses, and each route's own
unlock. Bamboo on perlite also needs Special Soils. A locked route prints
its requirement before clearing the world. The run reports net gain and
game time, so power used during mining is included in the net result.

The mushroom routine is adapted from
[Semy0nBu/the-farmer-was-replaced](https://github.com/Semy0nBu/the-farmer-was-replaced).
The coal depth-marker routine also draws on that project. The original
MIT notice is included in [LICENSE-MIT.txt](LICENSE-MIT.txt).
