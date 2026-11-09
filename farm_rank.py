from farm_rank_core import CATEGORY, SINGLE_DRONE, rank_profile

# Official leaderboard run. Set the category and drone count in farm_rank_core, then press Run here.
# The game uses an isolated inventory for repeated timing runs and submits a successful score to Steam.
# SPEEDUP controls playback speed. The default is suitable for most runs.
SPEEDUP = 40960
if CATEGORY == "bone" and SINGLE_DRONE:
    quick_print("[RANK STOP]", "Set SINGLE_DRONE = False for the dinosaur leaderboard.")
else:
    leaderboard, item, target, water = rank_profile(CATEGORY, SINGLE_DRONE)
    leaderboard_run(leaderboard, "farm_rank_entry", SPEEDUP)
