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
