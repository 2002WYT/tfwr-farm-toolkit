# 编程农场工具箱

适用于 Steam 游戏 [The Farmer Was Replaced《编程农场》](https://store.steampowered.com/app/2060160/The_Farmer_Was_Replaced/) 的收割、冲榜和测速脚本。日常入口覆盖作物、能量、金币、骨头和奇异物质。测试时，本体 15 个资源榜均取得 Steam 全球前 100 成绩。查看 [榜单复核与复现方法](docs/benchmarks.md)。

## 安装到游戏

1. 在游戏菜单选择 **加载 → 打开文件夹**，找到要使用的存档目录。先保存当前游戏并备份该目录。
2. 等当前收割结束或手动停止后，把本项目根目录的 `farm_*.py` 文件复制进存档目录。保留游戏生成的 `__builtins__.py` 与存档文件。
3. 重新加载该存档。日常脚本会用当前研究和库存，冲榜与模拟需要先解锁对应功能。

这些脚本由游戏内解释器运行。复制整套 `farm_*.py`，各入口需要同目录的辅助模块。

## 使用入口

| 用途 | 在哪里改 | 运行哪个窗口 |
|---|---|---|
| 日常收割 | `farm_run` 的 `MODE` 和 `ROUNDS` | `farm_run` |
| 正式冲榜 | `farm_rank_core` 的 `CATEGORY` 和 `SINGLE_DRONE` | `farm_rank` |
| 固定种子测速 | `farm_rank_lab` 的 `CASES` | `farm_rank_lab` |
| 回归检查 | `farm_test` 的 `SUITE` | `farm_test` |

仓库默认 `ROUNDS = 1`，便于先跑一轮再调大。`WORKERS = 0` 使用满编，`WATER_BELOW = 0` 关闭浇水。适用条件不满足时，各日常入口按策略回退或在播种前停止，输出原因。正式冲榜时，`VARIANT = -1` 选择已验证的版本。恐龙榜用 `SINGLE_DRONE = False`。正式成绩由游戏提交到 Steam。

游戏内可将 `farm_run`、`farm_rank_core` 和 `farm_rank` 保持展开。辅助窗口用 `−` 折叠，设置项旁已有中文注释。

## 算法与代码来源

- `farm_rank_hay_reference.py` 直接移植 enihsyou 的干草单机和多机路线，封装为可调用函数。
- `farm_bone_rail.py` 基于同一项目的恐龙波形源码改造。末尾苹果处理和第 8 版边线探测优化在本项目中实现。
- 其余资源榜实现、日常适配与测试由本项目编写。公开策略的引用、具体算法和适用条件见 [算法说明](docs/algorithms.md)。

两份上游衍生模块保留原作者版权声明和 MIT 许可证。查看 [第三方声明](THIRD_PARTY_NOTICES.md)。
