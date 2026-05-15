# 上一轮总结

迭代 23（2026-05-15）：IG OAS 上线，第五条指标，信用维度凑齐 HY+IG 一对。

本轮做了：
- DECISIONS.md 追加 ADR：IG OAS 阈值 GREEN<1.5 / YELLOW 1.5–3 / RED>3（up 方向）
  历史分位依据：平静期 0.8–1.5%、紧张期 2–3%、危机期 ≥5%（2008=6.5 / 2020 春=4.0）
  HY/IG 对照能区分"系统性信用收缩"vs"高收益独自承压"
- INDICATORS.md：新增 ig_oas 完整条目，P1 占位列表标记 ✅
- src/compute/indicators/ig_oas.py：FRED:BAMLC0A0CM → fetch + classify + upsert
  - NAME=ig_oas，DIRECTION=up，LOW=1.5 HIGH=3.0
  - 用 store helper，文件 60 行
- tests/test_ig_oas.py：5 classify + 4 fetch_and_store
- src/web/app.py：注册 "IG OAS 投资级利差"
- scripts/daily_fetch.py：FETCHERS 加 ig_oas

测试情况：
- pytest 共 106 通过 / 0 失败 / 0 skip（+9）

git：iter 22 bf83972 → iter 23 待 commit。

下一项 PLAN 顶上的 `[ ]`：
- **P1 第五项：VIX 期限结构（VIX vs VIX3M / VIX6M）**

VIX 期限结构需要单独考量，与"通过 fetch helper 拉单序列入库"模式不一样：
- 计算口径：通常是 VIX/VIX3M 比值（< 1 = 正向曲线即"近月低于远月"，市场平静；> 1 = 倒挂，恐慌临近）
- 数据源：VIX 已有（yfinance ^VIX）；VIX3M 需 yfinance ^VIX3M；可考虑 ^VIX6M
- 实现要点：fetch 两个序列 → 按日期 align → 计算比值 → 分类 → 入库（需要派生指标的写法）

下一轮决策点：阈值方案（推荐 GREEN <0.95 / YELLOW 0.95–1.0 / RED >1.0，up 方向 — 比值 ≥1 即倒挂）。
按"一直走推荐路线"指令，下一句"继续"将按上述方案落地，但实现需新增 store helper（双序列对齐+比值），可能触发"多文件改动"——iter 24 同时干。
