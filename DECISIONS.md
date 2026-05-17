# DECISIONS

> ADR 风格。每条一行：日期 / 决定 / 原因。重大架构与选型变更必须在这里留痕。

## 2026-05-15

- 选 SQLite 而非 Postgres：MVP 单机够用，零运维。后续上云若数据量超 1GB 再考虑迁移
- 选 Flask 而非 FastAPI：MVP 不需要异步与自动文档，模板渲染更直接
- 不引入 ORM：表结构稳定且简单，原生 SQL 维护成本更低
- 不上 Docker：本地开发 macOS 直跑速度最快
- 端口 5050（避开常用 5000）
- Python 3.9+ 兼容：用户机器上 Python 3.9 是系统默认
- 时间统一 UTC 入库，展示时转东八区
- 阈值默认值放代码常量，正式校准后写 INDICATORS.md，二者出现差异以 INDICATORS.md 为准
- 凡需注册账号才能拿 API key 的数据源（目前主要是 FRED），相关任务整体延后；用户后续会一次性把 key 写进 `.env`，届时再开做。PLAN.md 受影响项后缀 `⏸ 待 API key`，工作循环遇到时跳过往下找
- thresholds.classify 边界规则：`up` 方向 value==low→GREEN / value==high→YELLOW（要严格 > high 才 RED）；`down` 方向 value==high→GREEN / value==low→YELLOW（要严格 < low 才 RED）。与 INDICATORS.md 的 yield_curve_10y2y "RED < 0 / YELLOW 0–0.5 / GREEN > 0.5" 一致
- P0 首条上线指标走 **VIX via yfinance**（不需 API key，能立即让里程碑跑通）。FRED 路径并行推进，等用户给 key 后再做 10Y-2Y
- **yield_curve_10y3m 阈值采用 A 案**（与 10Y-2Y 同口径）：GREEN >0.5 / YELLOW 0–0.5 / RED <0，方向 down。理由：保持收益率曲线类指标横向可比；10Y-3M 历史波幅虽更大，但同切分有助于 dashboard 一眼看出"曲线维度"整体颜色一致性。后续若样本数据显示阈值需校准，再走 ADR 调整
- **iter 21 store helper 抽象触发**："重复三次再抽象"原则——vix.py / yield_curve.py / yield_curve_10y3m.py 三处共用的"遍历 series + NaN/Inf 跳过 + upsert"循环抽到 `src/store/db.py::upsert_series_from_pandas(conn, name, source, series) -> int`。三处 fetch_and_store 改为单行调用。db.py 保持零外部库依赖（NaN 用 `v != v` 判，Inf 用直接比较）
- **hy_oas 阈值采用推荐方案**：GREEN <4 / YELLOW 4–8 / RED >8，方向 up。理由：HY OAS（高收益债期权调整利差，单位百分点）历史分位——平静期 3–4%（2017、2021）、紧张期 5–7%（2022 末）、危机期 ≥10%（2008=18 / 2020 春=11）。8% 是市场已定价显著违约风险的临界点，4% 是利差正常上沿。后续视实测样本走 ADR 校准
- **ig_oas 阈值采用推荐方案**：GREEN <1.5 / YELLOW 1.5–3 / RED >3，方向 up。理由：IG OAS（投资级期权调整利差，单位百分点）历史分位远窄于 HY——平静期 0.8–1.5%（2021）、紧张期 2–3%（2022 末）、危机期 ≥5%（2008=6.5 / 2020 春=4.0）。3% 是 IG 市场已显著紧张的临界点（远高于经济周期上沿），1.5% 是平静上沿。HY/IG 两条对照能区分"系统性信用收缩"与"高收益独自承压"
- **vix_term_structure 阈值采用推荐方案**：GREEN <0.95 / YELLOW 0.95–1.0 / RED >1.0，方向 up。计算 VIX/VIX3M 比值。理由：contango（远月波动率溢价）是市场常态（比值 ~0.85–0.92），比值跨过 0.95 进入紧张区，跨过 1.0 转 backwardation 即近月恐慌定价超过 3 个月——历史上 2008 雷曼周、2020 春、2022 多次都曾跨过。指标本身没有"绝对量级"，0.95/1.0 切点稳定可参考
- **sofr_iorb 阈值采用推荐方案**：GREEN <0.05 / YELLOW 0.05–0.15 / RED >0.15（绝对值，bp），方向 up。计算 |SOFR - IORB|（或 SOFR - IORB 的正向偏离）。理由：SOFR 与 IORB 利差本应紧贴 0（联储靠 IORB 上限+ON RRP 下限框住 SOFR），偏离 5bp 已是流动性异常信号、偏离 15bp+ 即货币市场失灵（2019/9 回购危机当日 SOFR 飙到 IORB+300bp）。本指标用 abs(spread) 让"上下穿透"都能触发；后续若需区分上偏（融资紧张）/下偏（准备金过剩）再拆两个指标
- **iter 27 LLM 接入决策**：服务商=阿里百炼 Coding Plan（用户授权），协议=OpenAI 兼容 `/v1/chat/completions`，Auth=Bearer key 写 .env DASHSCOPE_API_KEY；模型 `qwen-max` 在 Coding Plan endpoint 实测不支持（400 invalid_parameter_error），改用 `qwen3-coder-plus`（实测可用，单次 ~300 字简报 prompt+output 19 tokens 量级）。依赖只用 requests（白名单内），不引 openai/anthropic SDK。失败优雅降级：LLM 不可用 daily_fetch 主流程不受影响

- **iter 28 跨市场维度首批指标决策**：先上 USDJPY（FRED:DEXJPUS 145/160）、DXY 广义（FRED:DTWEXBGS 110/125）、日本 10Y（FRED:IRLTLT01JPM156N 月值 1.0/2.0）三条，方向均为 up。USDJPY 不走 yfinance（有 rate limit）走 FRED 官方日值。日本 10Y 用 OECD 月值 IRLTLT01JPM156N（FRED 没免费日值 JGB）。BoJ 资产规模（JPNASSETS）暂搁——绝对量级阈值意义低，需要做"同比变化率"派生指标，等综合温度计做完后回头补
- **iter 29 综合温度计权重决策**：曲线 25% / 信用 25% / 跨市场 20% / 流动性 15% / 波动率 15%，合计 100%。理由：曲线是衰退最强先行（10Y-2Y 倒挂后 ~14 个月衰退）；信用是危机定价最快反应；跨市场抓 2025-26 主剧本（日元 carry / 强美元）；流动性是危机引爆器但平时低噪；波动率作弱权重（VIX 偶尔失灵）。Level → 分数线性（GREEN=0 / YELLOW=50 / RED=100），同 group 内算术平均，再按权重加权。总分阈值：< 25 GREEN / 25-65 YELLOW / ≥ 65 RED

## 2026-05-17

- **iter 33 [THESIS] 投资论点文档化**：用户反馈"按颜色和分数分组不够客观"，且发现项目 PROMPT/HANDOFF 都缺投资论点的根。基于用户与 Claude Opus 2026-05-14 对话沉淀正式 `THESIS.md`，包含：(1) 论点演化（"赌一波"→"穿越周期+尾部赚一笔"，Universa 路线 vs Burry 路线）；(2) 5 个候选崩盘剧本（美元荒/国债基差/日本 carry/AI 泡沫/信用估值滞后崩）；(3) 5 个反共识结构性观察；(4) §6 列出 9 类按"对崩盘监控价值"排序的缺失内容（历史回测 / z-score / 加速度 / 组合信号 / 融资市场维度 / 政策反应维度 / 波动率结构 / 跨市场补全 / 前端升级 / 仓位建议 / 失效条件）。同步更新 PROMPT.md（第一原则段 + 文档同步纪律 6 条检查清单）/ HANDOFF.md（必读清单加入 THESIS）/ README.md（顶部引用）/ PLAN.md（重排 P3 加 P3.6 真实优先级）。**核心纪律变化**：从此每轮代码改完后必须主动过 6 条文档同步清单，不等用户提醒
