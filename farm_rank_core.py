from farm_ops import run
from farm_mix import run_mix
from farm_gold import gold_geometry


# 【冲榜设置】通常只改 CATEGORY 和 SINGLE_DRONE，再到 farm_rank 点 ▶。
# CATEGORY 可选 hay 干草 / wood 木材 / carrot 胡萝卜 / pumpkin 南瓜
# power 向日葵 / cactus 仙人掌 / gold 迷宫 / bone 恐龙骨头
CATEGORY = "cactus"
# SINGLE_DRONE 为 True 时选单机榜，False 时选多机榜。bone 只能选 False。
SINGLE_DRONE = False
# MIXED 只影响 VARIANT = 0 的干草、木材和胡萝卜对照。
MIXED = True
# VARIANT 用 -1 自动选择实测版本。0 为旧版，正整数用于复测指定版本。
VARIANT = -1


def preferred_variant(mode, single):
    if VARIANT >= 0:
        return VARIANT
    # 每对数字依次为多机、单机。日常入口有自己的兼容性判断。
    variants = {
        "hay": (8, 8), "wood": (4, 2), "carrot": (6, 2), "pumpkin": (5, 5),
        "power": (3, 3), "cactus": (4, 2), "gold": (3, 3), "bone": (8, 8),
    }
    index = 0
    if single:
        index = 1
    return variants[mode][index]


def rank_profile(mode, single):
    if single:
        return {
            "hay": (Leaderboards.Hay_Single, Items.Hay, 100000000, 0),
            "wood": (Leaderboards.Wood_Single, Items.Wood, 500000000, 0.1),
            "carrot": (Leaderboards.Carrots_Single, Items.Carrot, 100000000, 0.1),
            "pumpkin": (Leaderboards.Pumpkins_Single, Items.Pumpkin, 10000000, 0.1),
            "power": (Leaderboards.Sunflowers_Single, Items.Power, 10000, 0.1),
            "cactus": (Leaderboards.Cactus_Single, Items.Cactus, 131072, 0),
            "gold": (Leaderboards.Maze_Single, Items.Gold, 616448, 0),
        }[mode]
    return {
        "hay": (Leaderboards.Hay, Items.Hay, 2000000000, 0),
        "wood": (Leaderboards.Wood, Items.Wood, 10000000000, 0.1),
        "carrot": (Leaderboards.Carrots, Items.Carrot, 2000000000, 0.1),
        "pumpkin": (Leaderboards.Pumpkins, Items.Pumpkin, 200000000, 0.1),
        "power": (Leaderboards.Sunflowers, Items.Power, 100000, 0.1),
        "cactus": (Leaderboards.Cactus, Items.Cactus, 33554432, 0),
        "gold": (Leaderboards.Maze, Items.Gold, 9863168, 0),
        "bone": (Leaderboards.Dinosaur, Items.Bone, 33488928, 0),
    }[mode]


def compete(mode, single):
    leaderboard, item, target, water = rank_profile(mode, single)
    workers = 0
    if single:
        workers = 1
    start = get_time()
    quick_print("[RANK START]", leaderboard, "target", target, "size", get_world_size(), "workers", workers)
    if MIXED and (mode == "hay" or mode == "wood" or mode == "carrot"):
        # 混种在整次冲榜中复用分区和伴生植物，达标后才清理。
        ok = run_mix(mode, 1, workers, water, target)
        if not ok or num_items(item) < target:
            quick_print("[RANK FAIL]", leaderboard, "current", num_items(item), "target", target)
            return False
        quick_print("[RANK PASS]", leaderboard, "current", num_items(item), "target", target,
                    "seconds", get_time() - start)
        return True

    rounds = 1
    if mode == "gold":
        # 单机复用整田迷宫，多机同时复用互不干扰的小迷宫。
        active, grid, stride, side = gold_geometry(get_world_size(), workers)
        scale = 2 ** (num_unlocked(Unlocks.Mazes) - 1)
        per_round = active * side ** 2 * scale
        rounds = max(1, (target - num_items(item) + per_round - 1) // per_round)
    while num_items(item) < target:
        before = num_items(item)
        ok = run(mode, rounds, workers, water)
        after = num_items(item)
        if not ok or after <= before:
            quick_print("[RANK FAIL]", leaderboard, "current", after, "target", target)
            return False
    quick_print("[RANK PASS]", leaderboard, "current", num_items(item), "target", target,
                "seconds", get_time() - start)
    return True
