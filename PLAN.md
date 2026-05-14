# PLAN

> 工作约定：每轮只做最上面一个 `[ ]`。完成后改成 `[x] (YYYY-MM-DD)`。
> 任务粒度需控制在单轮 30 分钟内完成；过粗的先拆。
>
> **API key 延后规则（2026-05-15 用户指令）**：所有需要注册账号才能拿到 key 的数据源
> （目前主要是 FRED）相关任务整体延后到用户一次性把 key 写进 `.env` 之后再做。
> 受影响项后缀标 `⏸ 待 API key`，遇到时跳过往下找下一个未阻塞的 `[ ]`。

## P0 — MVP 骨架（让系统能跑）

- [x] (2026-05-15) git init + .gitignore + 首个 commit
- [x] (2026-05-15) 创建 requirements.txt（fredapi, pandas, requests, yfinance, flask, plotly, python-dotenv, pytest）
- [x] (2026-05-15) 创建 .env.example（FRED_API_KEY=, TZ=Asia/Shanghai）
- [x] (2026-05-15) src 目录加 __init__.py，建立模块边界（fetch / compute / store / web / utils）
- [x] (2026-05-15) src/utils/logger.py：统一 logging，输出到 logs/app.log + stdout
- [x] (2026-05-15) src/utils/config.py：从 .env 读配置，集中管理常量
- [x] (2026-05-15) src/store/db.py：SQLite 连接 + indicators 表 schema（id, name, date, value, source, ingested_at）
- [ ] src/store/db.py：upsert_indicator(name, date, value, source) + get_latest(name) + get_series(name, days)
- [ ] tests/test_db.py：覆盖 upsert / 查询 / 重复插入
- [ ] src/fetch/fred_client.py：封装 fredapi，单方法 fetch_series(series_id, start) ⏸ 待 API key
- [ ] src/fetch/yf_client.py：封装 yfinance，单方法 fetch_close(ticker, start)
- [ ] tests/test_fetch.py：mock 外部，验证返回结构（先只覆盖 yf_client，FRED 部分 ⏸ 待 API key 后补）
- [ ] src/compute/thresholds.py：枚举三档（GREEN/YELLOW/RED）+ classify(value, low, high, direction) 通用函数
- [ ] tests/test_thresholds.py：覆盖正向/反向/边界
- [ ] 决策：P0 首条上线指标改用什么数据源（候选 A：VIX via yfinance；候选 B：等 FRED key 后再做 10Y-2Y）— 用户拍板后写 DECISIONS.md
- [ ] src/compute/indicators/yield_curve.py：10Y-2Y（FRED: T10Y2Y）实现 fetch+classify ⏸ 待 API key
- [ ] tests/test_yield_curve.py ⏸ 待 API key
- [ ] src/web/app.py：Flask 起一页 / 路由 → 列出所有已实现指标，名/当前值/颜色/更新时间
- [ ] templates/index.html：极简表格，颜色 inline style
- [ ] scripts/daily_fetch.py：跑一遍所有已注册 fetcher，写入 DB
- [ ] README 跑通指南：venv → pip → .env → daily_fetch → flask run，本地 http://localhost:5050 打开能看到 1 个指标
- [ ] 用户验收里程碑：localhost:5050 看到第一条绿色/黄色指标

## P1 — 加指标（每个一轮，每个都包含 fetch + classify + 测试 + INDICATORS.md 翻译卡占位）

- [ ] 10Y-3M（FRED: T10Y3M）⏸ 待 API key
- [ ] HY OAS（FRED: BAMLH0A0HYM2）⏸ 待 API key
- [ ] IG OAS（FRED: BAMLC0A0CM）⏸ 待 API key
- [ ] VIX（yfinance: ^VIX）
- [ ] VIX 期限结构（VIX vs VIX3M / VIX6M）
- [ ] SOFR-IORB（FRED: SOFR - IORB）⏸ 待 API key
- [ ] FRA-OIS（手动算或找代理序列）⏸ 待 API key（候选数据源都依赖 FRED）
- [ ] Shiller PE（Robert Shiller 网站 CSV）
- [ ] Buffett Indicator（Wilshire 5000 / GDP）
- [ ] Dashboard 加分组：曲线 / 信用 / 估值 / 流动性 / 波动率

## P2 — 跨市场联动

- [ ] USDJPY（yfinance: JPY=X）
- [ ] 日本 10Y 国债收益率
- [ ] 美元互换基差
- [ ] 国债基差交易杠杆估算（CFTC TFF 周报）
- [ ] 中国外汇储备月数据

## P3 — 解读层 & 综合温度计

- [ ] 每个指标 Dashboard 上加 90 天 sparkline（plotly）
- [ ] 综合温度计：六维度加权 → 单一风险分（0-100）
- [ ] INDICATORS.md 每个指标补足"翻译卡"（含义/误判/历史案例）— 等用户输入
- [ ] 仓位建议输出（基于综合温度计 → 风险敞口% / 对冲预算% / 现金%）
- [ ] 历史回测：2007-2008 / 2019-2020 套规则跑出来对比

## P4 — 自动化与运维

- [ ] launchd plist：每天美东 16:30 触发 daily_fetch
- [ ] 失败重试 + 日志轮转
- [ ] 数据缺失告警（连续 N 天没拿到 → 邮件/飞书）
- [ ] 备份脚本：每日 sqlite 拷贝到 ~/Backups/

## P5 — 上云（条件触发：系统稳定运行 1 个月以上）

- [ ] 选型 ADR：阿里云轻量 vs Hetzner vs GitHub Actions
- [ ] 部署脚本
- [ ] 域名 + HTTPS + 简单鉴权
- [ ] 推送通知（飞书/邮件）

## 后续构思（不进当前循环）

- 内容输出模板（每周风险周报）
- 交易日志接入
- 期权 IV/Skew 监控
- 宏观事件日历叠加
