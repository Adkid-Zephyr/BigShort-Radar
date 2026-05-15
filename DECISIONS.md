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
