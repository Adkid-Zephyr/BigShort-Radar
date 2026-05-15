# 上一轮总结

迭代 24-26（2026-05-15 自治模式）：MVP 阶段性可用 — 7 条指标 + 4 维分组 dashboard 上线，真实数据已入库。

本轮做了：
- iter 24：vix_term_structure（YF:^VIX/^VIX3M 比值派生指标）+ 推荐阈值 0.95/1.0 + 测试，commit 0a6c02a，pytest 118
- iter 25：sofr_iorb（FRED:SOFR-IORB 双序列差派生指标，bp 单位）+ 推荐阈值 5/15bp + 测试，commit 5349d7f，pytest 130
- iter 26：dashboard 分组 — 7 条指标按"波动率/信用/曲线/流动性"4 组聚合，组 header 显示组内最严等级；模板重写支持分组渲染，commit 2738959，pytest 133

真打验证（iter 26 收尾）：
- 5 条 FRED 指标（10Y2Y/10Y3M/HY/IG/SOFR-IORB）全部真打成功，共 ~3000 条历史日值入库
- VIX 与 vix_term_structure 触发 yfinance rate limit（短时反爬），单 fetcher 失败隔离机制工作正常，其他 6 个继续；VIX 沿用 iter 17 已入库 342 条数据，dashboard 正常显示
- Flask 起 localhost:5050 实景渲染：

| 维度 | 等级 | 数值 | 备注 |
|---|---|---|---|
| 波动率 | GREEN | VIX 17.26（5-14） | 平静 |
| 信用 | GREEN | HY 2.82 / IG 0.76（5-13） | 远低警戒 |
| 曲线 | YELLOW | 10Y2Y 0.48 偏平 / 10Y3M 0.77 健康 | 未倒挂 |
| 流动性 | YELLOW | SOFR-IORB 6.00 bp | 5-15bp 紧张区 |

测试情况：
- pytest 共 133 通过 / 0 失败 / 0 skip（自治三轮共 +27 用例）
- 7 个 fetcher 注册，6 个真打验证通过

git：iter 23 c82cfbb → iter 24 0a6c02a → iter 25 5349d7f → iter 26 2738959

## ⏸ 决策点（自治终止条件触发，等用户拍板）

PLAN P1 还有 3 项被标 ⏸：

1. **FRA-OIS** — LIBOR 退役后 FRA 已停发，FRED 无现成序列。候选代理：
   - (A) USD3M T-bill - SOFR
   - (B) DTCC GCF Repo - SOFR
   - (C) 直接跳过此项

2. **Shiller PE** — 数据源是 Robert Shiller 个人网站 .xls，pandas 解析需 xlrd 或 openpyxl，**触发暂停清单第 1 条（白名单外依赖）**。可选：
   - (A) 加白名单依赖 openpyxl
   - (B) 走 multpl.com HTML 抓取（仅当前值，无历史）
   - (C) 跳过此项

3. **Buffett Indicator** — FRED 有 WILL5000PRFC（日）和 GDP（季度），需要"日值/季度值前向填充"对齐。问题：季度 GDP 滞后 3 个月，作为崩盘监控敏感度低。可选：
   - (A) 做（接受滞后）
   - (B) 跳过，先用其他估值代理（如 P/B、市值/M2）
   - (C) 完全弃用

## MVP 当前可用状态

- ✅ 4 维度风险温度计（波动率/信用/曲线/流动性）
- ✅ 7 条核心指标，5 条真实数据已入库
- ✅ Dashboard 实景可看
- ✅ daily_fetch 全自动，单 fetcher 失败不影响其他
- ✅ 阈值与方向全部 ADR 留痕
- ✅ pytest 133 / 0
- ⏳ 缺：估值维度（Shiller / Buffett 需用户决策）；自动化（cronjob/launchd）；P3 综合温度计；P4 通知

下一步用户决策方向：
- A 路线：拍板 FRA/Shiller/Buffett 三项，把 P1 完整封口
- B 路线：直接进 P4 自动化（launchd 每天美东 16:30 自动跑），让系统真正"无人值守监控"
- C 路线：进 P3 综合温度计（六维度加权 → 单一风险分 0-100）
