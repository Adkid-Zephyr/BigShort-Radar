# 上一轮总结

迭代 53（2026-05-17）：2022 加息熊市窗口 + 三窗口对比 SUMMARY.md。

## 本轮做了

### A. 2022 窗口
- backtest_window 2022-01-01 ~ 2023-06-30 跑 546 天
- 输出 data/backtest_results/rate_hike_2022.csv
- score min=10.6 max=82.07 mean=44.8
- GREEN 33 / YELLOW 474 / **RED 39 天（27 天集中 2022-10）**
- 关键日：2022-10-18 score 82.07（英国 LDI 危机顶峰）

### B. SUMMARY.md 报告生成
- src/backtest/report.py:
  - load_window / summarize_window / render_summary_md / generate_summary
- 输出 data/backtest_results/SUMMARY.md（两窗口对比 + 缺失模式分析）

### 🔑 关键发现：缺失模式定位 iter 55 校准方向

| 指标 | 缺失率 | 原因 |
|---|---:|---|
| vix / vts / vvix / skew | 100% | cache DB 没回填（主流程 daily_fetch 累积主 DB） |
| sofr_iorb / fra_ois | 100% | 派生指标 cache 跳过 |
| china_10y | 100% | FRED IRLTLT01CNM156N series 不存在 |
| hy_oas / ig_oas | 96% | FRED 历史只到 2023 |

**两个解决方向**（iter 55 拍板）：
1. cache DB 同步主 DB 派生指标（让 vix/vts/sofr_iorb 等也写 cache）
2. 综合分改"维度内最严触顶"机制（任一指标 RED → 维度 RED）

### C. 测试
- 8 个新测试（test_backtest_report.py）
- pytest 484 → 492

git iter 52 e65687f → 53 待 commit

## 下一轮（iter 54）
2008 雷曼周窗口：
- 跑 backtest_window("2008-01-01", "2009-06-30")
- 用 vix_fred + ted_spread 代理（SOFR/IORB/ON RRP/HY OAS 都缺）
- ted_spread 2008-09 一度 4.58%，应触发持续 RED
- 输出 lehman_2008.csv 加进 SUMMARY

下一句"继续"将进 iter 54。
