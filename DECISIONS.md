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
