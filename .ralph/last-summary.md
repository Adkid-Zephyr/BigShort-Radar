# 上一轮总结

迭代 29（2026-05-15）：综合风险温度计上线，dashboard 顶部出现 27/100 YELLOW 大数字。

本轮做了：
- src/compute/risk_score.py：compute_score / risk_scores 表 / get_latest / run_and_store
- 权重 ADR：曲线 25 / 信用 25 / 跨市场 20 / 流动性 15 / 波动率 15（合 100%）
- Level → 分数线性（GREEN=0 / YELLOW=50 / RED=100），同 group 内取均值，再加权
- 总分阈值：<25 GREEN / 25-65 YELLOW / ≥65 RED
- tests/test_risk_score.py：9 用例（compute / breakdown / 缺数据 / 阈值 / run_and_store / overwrites）
- daily_fetch 跑完先算分再调 LLM；briefing 喂 prompt 时附带综合分上下文
- web/app.py 与 templates/index.html 加 .gauge 大数字卡片（含维度分解一行）

测试 + 真打：
- pytest 共 163 通过 / 0 失败 / 0 skip（+9）
- 真打 daily_fetch：score=27.08 YELLOW，跨市场 67/100 最高（USDJPY YELLOW + JP10Y RED 拉高）
- LLM 简报已识别"日本 10 年期国债收益率维持在红色警戒水平 2.345%"

git：iter 28 1f5bdce → iter 29 待 commit。

下一项 PLAN：
- **iter 30：/chat 对话接口** — 用户能就当前指标追问 LLM（用户 5/15 14:18 提的 chatbot 需求）
- iter 31：launchd 自动化（每天美东 16:30 自动跑）
- iter 32：前端打磨（dashboard 视觉升级，准备成"产品"）
- iter 33：GitHub 准备（README、scrub 检查、推上去）

按用户授权"按计划做下去"，下一句"继续"将进 iter 30。
