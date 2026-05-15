# 上一轮总结

迭代 28（2026-05-15）：跨市场 3 条指标上线，dashboard 加"跨市场"分组。

本轮做了：
- src/compute/indicators/usdjpy.py（FRED:DEXJPUS 日值）阈值 145/160 up
- src/compute/indicators/dxy.py（FRED:DTWEXBGS 日值）阈值 110/125 up
- src/compute/indicators/jp_10y.py（FRED:IRLTLT01JPM156N 月值）阈值 1.0/2.0 up
- tests/test_jp_dxy_indicators.py：3 指标各 2 用例（classify + fetch_and_store）共 6 通过
- INDICATORS.md / DECISIONS.md 同步 ADR
- web/app.py + daily_fetch.py 注册三条；新增"跨市场"分组排第 5
- PLAN.md：P3.5 三项打勾，BoJ YoY、JP30Y 等留作后续

测试 + 真打：
- pytest 共 154 通过（+6）
- daily_fetch 真打：USDJPY 590 条、DXY 590 条 入库；IG/JP10Y 因 FRED 500 偶发失败（重试可恢复）；VIX/vix_term 仍 yfinance rate limit

git：iter 27 f45bc38 → iter 28 待 commit。

下一项 PLAN 顶上的工作：
- **iter 29：综合温度计**（七维加权 → 单一 0-100 风险分）
  - 7 + 跨市场 3 = 10 条指标，按维度权重加权（推荐：曲线 25 / 信用 25 / 流动性 15 / 波动率 15 / 跨市场 20）
  - 每条指标按 GREEN=0 / YELLOW=50 / RED=100 转分数，组内取平均
  - 维度分 × 维度权重 = 总分
  - 写库新表 risk_score(date, score, breakdown_json, created_at)
  - dashboard 顶部 briefing 之上加"风险温度计"大数字

按用户授权"按计划做下去"，下一句"继续"将进 iter 29。
