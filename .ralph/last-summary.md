# 上一轮总结

迭代 19（2026-05-15）：yield_curve_10y2y 上线，第二条指标接入 dashboard 与 daily_fetch。

本轮做了：
- src/compute/indicators/yield_curve.py：FRED:T10Y2Y → fetch + classify_value + upsert
  - NAME = "yield_curve_10y2y"，SOURCE = "FRED:T10Y2Y"，DIRECTION = "down"
  - 阈值常量与 INDICATORS.md 一致：LOW=0.0 / HIGH=0.5
  - 结构与 vix.py 对齐（fetch + 遍历 + upsert，NaN/Inf 跳过）；按 DECISIONS.md "重复三次再抽象"，本轮不抽 helper
- tests/test_yield_curve.py：5 个 classify 边界 + 4 个 fetch_and_store（写入/空/幂等/NaN 跳过）
- src/web/app.py：_INDICATOR_REGISTRY 加 "10Y-2Y 收益率曲线" 一项
- scripts/daily_fetch.py：FETCHERS 加 yield_curve_10y2y

测试情况：
- pytest 共 74 通过 / 0 失败 / 0 skip（+9 新用例）
- 既有 65 全保留无破坏

git：housekeeping 2cd5195（HANDOFF.md + last-summary 补刷）→ iter 19 待 commit。

下一项 PLAN 顶上的 `[ ]`：
- **P1 第一项：10Y-3M（FRED: T10Y3M）实现 fetch+classify+测试**

实现路径：与 yield_curve_10y2y 同款（结构第三次出现）。
**重要**：完成 10Y-3M 时，按 DECISIONS.md "重复三次再抽象"——同一轮内或紧接一轮，把 vix.py / yield_curve.py / 10Y3M.py 三处共用的"遍历 series 写库"段抽到 store 层 helper 并回填三处。

10Y-3M 还需要：
- INDICATORS.md 加条目（阈值、方向、翻译卡占位"待用户补"）——该指标目前还没在 INDICATORS.md 定义
- 阈值方向同 10Y-2Y（down 越低越危险），具体阈值待 ADR：常用经验值 GREEN > 1.0 / YELLOW 0–1.0 / RED < 0，也可与 10Y-2Y 对齐用 0.5 切分。建议下一轮先在 DECISIONS.md 备一条然后落地。
