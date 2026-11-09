# Entry point for simulate() in farm_test.py. The simulator supplies the settings.
from farm_ops import run
from farm_bones import run_bones
from farm_rank_core import compete, rank_profile
from farm_substance import run_substance
from farm_mix import run_mix


def surface_is_untouched(size, allowed_crop):
    soil_tiles = 0
    crop_tiles = 0
    for x in range(size):
        for y in range(size):
            ground = get_ground_type()
            entity = get_entity_type()
            if ground == Grounds.Soil:
                soil_tiles += 1
            elif ground != Grounds.Grassland:
                return False
            if allowed_crop != None and entity == allowed_crop and ground == Grounds.Soil:
                crop_tiles += 1
            elif entity != None and entity != Entities.Grass:
                return False
            move(North)
        move(East)
    if allowed_crop == None:
        return soil_tiles == 0 and crop_tiles == 0
    return soil_tiles == 1 and crop_tiles == 1


def surface_has_water(size):
    for x in range(size):
        for y in range(size):
            if get_water() > 0:
                return True
            move(North)
        move(East)
    return False


def output_item(mode):
    return {
        "hay": Items.Hay,
        "wood": Items.Wood,
        "carrot": Items.Carrot,
        "pumpkin": Items.Pumpkin,
        "power": Items.Power,
        "cactus": Items.Cactus,
        "gold": Items.Gold,
        "substance": Items.Weird_Substance,
        "water": Items.Water,
        "fertilizer": Items.Fertilizer,
    }[mode]


def test_bones():
    if setup == "occupied":
        move(West)
        move(South)
        till()
        if not plant(Entities.Carrot):
            quick_print("[TEST] FAIL", label, "fixture did not plant")
            return

    started = get_time()
    before = num_items(Items.Bone)
    cactus = num_items(Items.Cactus)
    if setup == "cycle":
        ok = run_bones(rounds, False)
    elif setup == "full-baseline":
        ok = run_bones(rounds, True, False)
    else:
        ok = run(mode, rounds, workers, water_below)
    elapsed = get_time() - started
    gain = num_items(Items.Bone) - before
    spent = cactus - num_items(Items.Cactus)
    length = size * size - 1
    if setup == "five-apples":
        length = 5
    expected = rounds * length ** 2 * 2 ** (num_unlocked(Unlocks.Dinosaurs) - 1)
    should_run = size % 2 == 0 and setup != "occupied" and setup != "no-apple"
    if not should_run:
        expected = 0
    quick_print("[TIME]", label, "mode", "bone", "size", size, "seed", seed,
                "seconds", elapsed, "gain", gain, "cactus_spent", spent)
    preserved = True
    if setup == "occupied":
        preserved = surface_is_untouched(size, Entities.Carrot)
    if ok == should_run and gain == expected and preserved and (should_run or spent == 0):
        quick_print("[TEST] PASS", label, "gain", gain, "expected", expected, "preserved", preserved)
    else:
        quick_print("[TEST] FAIL", label, "ok", ok, "gain", gain, "expected", expected,
                    "cactus_spent", spent, "preserved", preserved)


def test_extra():
    item = output_item(mode)
    before = num_items(item)
    started = get_time()
    if mode == "substance" and setup == "cross":
        ok = run_substance(rounds, workers, "cross", water_below)
    else:
        ok = run(mode, rounds, workers, water_below)
    elapsed = get_time() - started
    gain = num_items(item) - before
    rate = 0
    if elapsed > 0:
        rate = gain * 60 / elapsed
    quick_print("[TIME]", label, "mode", mode, "size", size, "workers", workers,
                "seed", seed, "seconds", elapsed, "gain", gain, "net_per_min", rate)
    if setup == "gold-poor":
        passed = not ok and gain == 0 and surface_is_untouched(size, None)
    elif mode == "water" or mode == "fertilizer":
        research = Unlocks.Watering
        if mode == "fertilizer":
            research = Unlocks.Fertilizer
        expected = (elapsed / 10) * 2 ** (num_unlocked(research) - 1)
        passed = ok and abs(gain - expected) < 2
    else:
        passed = ok and gain > 0
    if passed:
        quick_print("[TEST] PASS", label, "gain", gain)
    else:
        quick_print("[TEST] FAIL", label, "ok", ok, "gain", gain)


def test_rank():
    single = size == 8
    leaderboard, item, target, water = rank_profile(mode, single)
    started = get_time()
    ok = compete(mode, single)
    quick_print("[TIME]", label, "mode", mode, "size", size, "seconds", get_time() - started,
                "current", num_items(item), "target", target)
    if ok and num_items(item) >= target:
        quick_print("[TEST] PASS", label, leaderboard)
    else:
        quick_print("[TEST] FAIL", label, leaderboard)


def test_mixed():
    item = output_item(mode)
    protected = setup == "mix-existing"
    if protected:
        move(West)
        move(South)
        till()
        if not plant(Entities.Carrot):
            quick_print("[TEST] FAIL", label, "fixture did not plant")
            return
    before = num_items(item)
    start = get_time()
    if setup == "mix-base":
        ok = run(mode, rounds, workers, water_below)
    else:
        ok = run_mix(mode, rounds, workers, water_below)
    elapsed = get_time() - start
    gain = num_items(item) - before
    preserved = True
    if protected:
        while get_pos_x() != size - 1:
            move(East)
        while get_pos_y() != size - 1:
            move(North)
        preserved = get_entity_type() == Entities.Carrot and get_ground_type() == Grounds.Soil
    rate = 0
    if elapsed > 0:
        rate = gain * 60 / elapsed
    quick_print("[TIME]", label, "mode", mode, "size", size, "workers", workers, "seed", seed,
                "seconds", elapsed, "gain", gain, "net_per_min", rate)
    if ok and gain > 0 and preserved:
        quick_print("[TEST] PASS", label, "protected", preserved)
    else:
        quick_print("[TEST] FAIL", label, "ok", ok, "gain", gain, "protected", preserved)


def test():
    set_world_size(size)
    if get_world_size() != size:
        quick_print("[TEST] FAIL", label, "world size", get_world_size(), "expected", size)
        return

    if setup == "rank" or setup == "rank-full":
        test_rank()
        return

    if setup == "mix-base" or setup == "mix" or setup == "mix-existing" or setup == "mix-budget":
        test_mixed()
        return

    if mode == "bone":
        test_bones()
        return

    if mode == "gold" or mode == "substance" or mode == "water" or mode == "fertilizer":
        test_extra()
        return

    if setup == "bare-soil":
        for x in range(size):
            for y in range(size):
                till()
                move(North)
            move(East)

    if setup == "occupied" or setup == "resume":
        move(West)
        move(South)
        till()
        crop = Entities.Carrot
        if not plant(crop):
            quick_print("[TEST] FAIL", label, "fixture did not plant", crop)
            return

    item = output_item(mode)
    initial = num_items(item)
    hay = num_items(Items.Hay)
    wood = num_items(Items.Wood)
    carrots = num_items(Items.Carrot)
    water = num_items(Items.Water)
    started = get_time()
    result = run(mode, rounds, workers, water_below)
    elapsed = get_time() - started
    gain = num_items(item) - initial
    water_used = water - num_items(Items.Water)
    quick_print("[TIME]", label, "mode", mode, "size", size, "workers", workers,
                "seed", seed, "seconds", elapsed, "gain", gain, "net_water_used", water_used)

    if setup == "shortage" or setup == "occupied":
        if setup == "shortage":
            cost = get_cost(Entities.Pumpkin)
            for ingredient in cost:
                budget = cost[ingredient] * (size * size - 1)
                if num_items(ingredient) != budget:
                    quick_print("[TEST] FAIL", label, "expected one seed short", ingredient,
                                "have", num_items(ingredient), "expected", budget)
                    return
        unchanged = (gain == 0 and num_items(Items.Hay) == hay and num_items(Items.Wood) == wood
                     and num_items(Items.Carrot) == carrots and water_used <= 0)
        allowed_crop = None
        if setup == "occupied":
            allowed_crop = Entities.Carrot
        preserved = surface_is_untouched(size, allowed_crop)
        if result == False and unchanged and preserved:
            quick_print("[TEST] PASS", label, "rejected and preserved field and inventory")
        else:
            quick_print("[TEST] FAIL", label, "result", result, "inventory preserved", unchanged, "field preserved", preserved)
        return

    if result != True or gain <= 0:
        quick_print("[TEST] FAIL", label, "result", result, "gain", gain)
        return
    if water_below == 0 and water_used > 0:
        quick_print("[TEST] FAIL", label, "watering disabled", "water used", water_used)
        return
    if water_below > 0 and water_used <= 0 and not surface_has_water(size):
        quick_print("[TEST] FAIL", label, "watering enabled", "water used", water_used)
        return

    # Batch yields for uninfected crops on a single surface.
    expected = None
    if mode == "cactus":
        expected = rounds * size ** 4 * 2 ** (num_unlocked(Unlocks.Cactus) - 1)
    elif mode == "pumpkin":
        expected = rounds * size * size * min(size, 6) * 2 ** (num_unlocked(Unlocks.Pumpkins) - 1)
    if expected != None and gain != expected:
        quick_print("[TEST] FAIL", label, "batch gain", gain, "expected", expected)
        return

    # Trees and companion plants can raise the per-tile yield.
    minimum = 1
    if mode == "hay":
        minimum = rounds * size * size * 2 ** max(0, num_unlocked(Unlocks.Grass) - 1)
    elif mode == "carrot":
        minimum = rounds * size * size * 2 ** (num_unlocked(Unlocks.Carrots) - 1)
    elif mode == "wood":
        minimum = rounds * size * size * 2 ** max(0, num_unlocked(Unlocks.Trees) - 1)
    if gain < minimum:
        quick_print("[TEST] FAIL", label, "batch gain", gain, "minimum", minimum)
        return

    quick_print("[TEST] PASS", label, "gain", gain, "exact", expected, "minimum", minimum)


test()
