from farm_rank_candidate import candidate
from farm_rank_core import CATEGORY, SINGLE_DRONE, preferred_variant, rank_profile

# The game calls this file for timing. Run farm_rank to start an official challenge.
leaderboard, item, target, water = rank_profile(CATEGORY, SINGLE_DRONE)
variant = preferred_variant(CATEGORY, SINGLE_DRONE)
start = get_time()
ok = candidate(CATEGORY, SINGLE_DRONE, variant)
quick_print("[NATIVE]", CATEGORY, SINGLE_DRONE, "variant", variant, "seconds", get_time() - start,
            "output", num_items(item), "target", target, "passed", ok and num_items(item) >= target)
