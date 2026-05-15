# 上一轮总结

迭代 21（2026-05-15）：store helper 抽象 + 三处回填，"重复三次再抽象"原则落地。

本轮做了：
- src/store/db.py 新增 `upsert_series_from_pandas(conn, name, source, series) -> int`
  - 抽象自 vix.py / yield_curve.py / yield_curve_10y3m.py 共用循环
  - NaN 检测用 `v != v`（不依赖 math），Inf 直接比较——db.py 维持零外部库
  - None / 空 series → 返回 0；单行错误（无法转 float / NaN / Inf）跳过+log
- 三处指标文件 fetch_and_store 简化为单行调用 helper：
  - vix.py：80 行 → 58 行（去掉 math 导入与遍历循环）
  - yield_curve.py：80 行 → 58 行（同上，去掉手册段）
  - yield_curve_10y3m.py：80 行 → 58 行（同上，去掉延后注释）
- tests/test_db.py 补 5 个 helper 用例：写入/None/空/NaN+Inf 跳过/幂等
- DECISIONS.md 追加 iter 21 ADR

测试情况：
- pytest 共 88 通过 / 0 失败 / 0 skip（+5）
- 三处指标既有测试零回归（mock 路径仍走 fetch_and_store → helper）
- db.py 233 行（< 300 阈值线）

git：iter 20 d8006bf → iter 21 待 commit。

下一项 PLAN 顶上的 `[ ]`：
- **P1 第三项：HY OAS（FRED: BAMLH0A0HYM2）**

实现路径（用新 helper，每个指标文件预期 ~58 行）：
- 新文件 `src/compute/indicators/hy_oas.py`，方向 up（OAS 利差越宽越危险，信用市场紧张）
- 阈值待 ADR：参考历史经验 GREEN <4% / YELLOW 4–8% / RED >8%（高收益债 OAS 单位是百分点）
  危机时 HY OAS 飙到 10%+（2008 = 18%、2020 春 = 11%、2022 末 = 5.8%）。需要拍板。
- INDICATORS.md 加完整条目；DECISIONS.md 备案阈值依据
- web/app.py 与 daily_fetch.py 同步注册

下一轮决策点：HY OAS 阈值切点。
推荐：GREEN <4 / YELLOW 4–8 / RED >8（保守口径，利差 8%+ 意味着市场已定价显著违约风险）。
按用户"一直走推荐路线"指令，下一句"继续"将直接按此方案落地，无需再问。
