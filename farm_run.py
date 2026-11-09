from farm_ops import run
from farm_daily_crops import run_power_daily, run_pumpkin_daily
from farm_daily_fast import run_bones_daily, run_cactus_daily, run_gold_preferred
from farm_daily_mixfast import run_daily_mixfast
from farm_daily_poly import run_wood_daily

# 【日常设置】改好参数后，点本窗口左上角 ▶。第一次试跑可设 ROUNDS = 1。
# MODE 可选
# hay 干草 / wood 木材 / carrot 胡萝卜 / pumpkin 南瓜 / power 向日葵能量
# cactus 仙人掌 / bone 恐龙骨头 / gold 迷宫金币 / substance 奇异物质
# water 水 / fertilizer 肥料
MODE = "hay"
# ROUNDS 是收获轮数。金币每轮每座迷宫收一箱，水和肥料每轮等待 10 游戏秒。
ROUNDS = 1

# WORKERS 为 0 时用满编，1 为单机。恐龙路线由一架无人机完成。
WORKERS = 0
# WATER_BELOW 为 0 时关闭浇水，0.1 表示水位低于 10% 才补水。
WATER_BELOW = 0
# MIXED 为 True 时，干草、木材和胡萝卜启用伴生路线。
MIXED = True

# 【收割入口】这里根据设置选路线。
if MODE == "cactus":
    run_cactus_daily(ROUNDS, WORKERS, WATER_BELOW, 4)
elif MODE == "gold":
    run_gold_preferred(ROUNDS, WORKERS)
elif MODE == "bone":
    run_bones_daily(ROUNDS, True)
elif MODE == "pumpkin":
    run_pumpkin_daily(ROUNDS, WORKERS, WATER_BELOW)
elif MODE == "power":
    run_power_daily(ROUNDS, WORKERS, WATER_BELOW)
elif MIXED and MODE == "wood":
    run_wood_daily(ROUNDS, WORKERS, WATER_BELOW)
elif MIXED and (MODE == "hay" or MODE == "carrot"):
    run_daily_mixfast(MODE, ROUNDS, WORKERS, WATER_BELOW)
else:
    run(MODE, ROUNDS, WORKERS, WATER_BELOW)
