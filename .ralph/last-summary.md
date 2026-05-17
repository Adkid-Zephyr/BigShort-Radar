# 上一轮总结

迭代 52（2026-05-17）：历史回测引擎股架 + 数据准备 + 2020 COVID 验证窗口（第三阶段开端）。

## 本轮做了

### A. 重构（"重复三次抽象"原则）
- src/compute/risk_score.py: 抽出 score_from_indicator_values(name_to_value, registry)
- compute_score 改为先取 latest 值再调 helper

### B. 新建 src/backtest/ 模块
- registry.py: BACKTEST_INDICATORS = 主流程 19 + vix_fred(FRED:VIXCLS) + ted_spread(FRED:TEDRATE)
- score.py: compute_score_for_date 含 forward-fill (≤10 天)
- engine.py: backtest_window CLI + write_csv

### C. 数据扩展
- backfill_history.py 加 --backtest 标志
- 跑 --start 2006-01-01 后 cache DB 9696 → 38059 条
- vix_fred 5152 条覆盖 1990 起完整 VIX
- ted_spread 3942 条覆盖 LIBOR 退役前（2006-2022）
- LIBOR USD3MTD156N FRED 停发 → 改用 TED Spread 经典度量
- china_10y FRED IRLTLT01CNM156N series 不存在 → 标 BLOCKED 留 iter 56 用户人工取

### D. COVID 2019-09 ~ 2020-12 验证窗口
- 488 天回测跑通，输出 data/backtest_results/covid_2020.csv
- score min=20.2 / max=52.1 / mean=28.1
- GREEN 177 / YELLOW 311 / **RED 0 天**

### 🔑 关键发现：阈值偏迟钝
COVID 黑色星期一 (2020-03-19)：
- VIX_FRED 72.0（远超 RED 阈值 30）
- TED 1.16（超 RED 阈值 1.0）
- 但综合分 51.67 YELLOW（被 11 个 missing 指标稀释）

**iter 55 阈值校准会基于这个数据建议改权重或切点**。

### E. 测试
- 26 个新测试（test_backtest_score 14 + test_backtest_engine 12）
- pytest 458 → 484

git iter 51 70f6a18 → 52 待 commit

## 下一轮（iter 53）
2022 加息熊市窗口（数据完整）+ 三窗口对比报告：
- 跑 backtest_window("2022-01-01", "2023-06-30") 出 2022.csv
- 把 covid_2020.csv 与新 2022.csv 对比分析
- 输出 data/backtest_results/SUMMARY.md（关键日期 + level 分布 + missing 模式）

下一句"继续"将进 iter 53。
