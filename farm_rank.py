from farm_rank_core import CATEGORY, SINGLE_DRONE, rank_profile

# 【正式冲榜】在 farm_rank_core 选好项目和组别，再点本窗口左上角 ▶。
# 游戏用独立库存重复计时，达标后提交 Steam 成绩。
# SPEEDUP 只调比赛播放速度，保持默认即可。
SPEEDUP = 40960
if CATEGORY == "bone" and SINGLE_DRONE:
    quick_print("[RANK STOP]", "恐龙榜请选择 SINGLE_DRONE = False")
else:
    leaderboard, item, target, water = rank_profile(CATEGORY, SINGLE_DRONE)
    leaderboard_run(leaderboard, "farm_rank_entry", SPEEDUP)
