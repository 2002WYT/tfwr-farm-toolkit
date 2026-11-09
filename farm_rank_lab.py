# 改 CASES 可复测同一批次。每项依次为资源、是否单机、候选版本、随机种子。
CASES = [("cactus", False, 3, 1709), ("cactus", True, 3, 1709),
         ("cactus", False, 2, 1709), ("cactus", True, 2, 1709),
         ("gold", False, 3, 1709), ("gold", True, 3, 1709),
         ("hay", False, 3, 1709), ("hay", True, 3, 1709),
         ("wood", False, 3, 1709), ("wood", True, 3, 1709),
         ("carrot", False, 3, 1709), ("carrot", True, 3, 1709),
         ("pumpkin", False, 3, 1709), ("pumpkin", True, 3, 1709),
         ("power", False, 3, 1709), ("power", True, 3, 1709)]


def supplies(mode):
    items = {Items.Power: 1000000000}
    if mode == "carrot":
        items[Items.Hay] = 1000000000
        items[Items.Wood] = 1000000000
    elif mode == "pumpkin" or mode == "power":
        items[Items.Carrot] = 1000000000
        if mode == "power":
            items[Items.Power] = 0
    elif mode == "cactus":
        items[Items.Pumpkin] = 1000000000
    elif mode == "gold":
        items[Items.Weird_Substance] = 1000000000
    elif mode == "bone":
        items[Items.Cactus] = 1000000000
    return items


def sweep(cases):
    for mode, single, variant, seed in cases:
        settings = {"mode": mode, "single": single, "variant": variant, "seed": seed}
        research = Unlocks
        stock = supplies(mode)
        if variant < 0:
            # 日常对照继承当前存档的研究等级，且在独立库存里执行。
            research = {}
            for technology in Unlocks:
                level = num_unlocked(technology)
                if level > 0:
                    research[technology] = level
            stock[Items.Power] = 100000
            if mode == "wood" or mode == "hay":
                stock[Items.Hay] = 10000000
                stock[Items.Wood] = 10000000
            if variant <= -6:
                stock[Items.Water] = 10000
        quick_print("[LAB CASE]", mode, single, variant, seed)
        elapsed = simulate("farm_rank_probe", research, stock, settings, seed, 40960)
        quick_print("[LAB SIM]", mode, single, variant, seed, elapsed)
    quick_print("[LAB COMPLETE]", len(cases))


if __name__ == "__main__":
    sweep(CASES)
