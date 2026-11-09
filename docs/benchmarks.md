# In-game benchmarks

These scores were verified on the Steam global leaderboards on November 9, 2026. Times are in game seconds. Single-drone and multi-drone categories were verified separately. Dinosaurs have one resource leaderboard. The game runs multiple random seeds before submitting an official score. Rankings may have changed since this snapshot.

| Resource | Multi-drone time (s) | Multi-drone rank | Single-drone time (s) | Single-drone rank |
|---|---:|---:|---:|---:|
| Hay | 111.864 | 71 | 171.675 | 73 |
| Wood | 300.756 | 86 | 424.519 | 73 |
| Carrots | 263.990 | 52 | 364.775 | 67 |
| Pumpkins | 423.278 | 83 | 485.940 | 93 |
| Sunflower power | 260.524 | 15 | 327.416 | 11 |
| Cactus | 34.968 | 67 | 19.712 | 43 |
| Maze gold | 119.718 | 82 | 144.732 | 63 |
| Dinosaur bones | 798.084 | 73 | — | — |

## Reproduce a benchmark

Add `(mode, single_drone, variant, seed)` entries to `CASES` in `farm_rank_lab.py` and run that window in the game. Each `[LAB]` line reports elapsed game seconds, the collected quantity, the target, and whether the run met it. `preferred_variant` in `farm_rank_core.py` lists the versions selected for the official runs. Seeds `1709` and `8243` were used for several comparisons.

This example compares multi-drone carrot variants 3 and 6. Both aim to collect 2 billion carrots.

```python
CASES = [("carrot", False, 3, 1709), ("carrot", False, 6, 1709)]
```

Variant 3 took 300.58 seconds and variant 6 took 264.75 seconds. The official run took 263.990 seconds.

## Daily harvesting checks

- With all drones and watering disabled, wood output rose from about 558–571 million to 1.188–1.201 billion per game minute on seeds `1709` and `8243`.
- With all drones on seed `1709`, cactus output rose from about 24.41 million to 28.88 million per game minute.
- With the daily save's research levels and seed `1709`, dinosaur variant 8 collected 8,372,232 bones in 811.20 seconds. A low-stock case used materials for five apples and collected 200 bones.

Daily results depend on the save's research levels, inventory, and field. Simulation cases with negative variant numbers use the current research levels and an isolated test inventory.
