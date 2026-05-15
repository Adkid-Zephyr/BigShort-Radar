# PLAN

> 工作约定：每轮只做最上面一个 `[ ]`。完成后改成 `[x] (YYYY-MM-DD)`。
> 任务粒度需控制在单轮 30 分钟内完成；过粗的先拆。
>
> **API key 状态**：FRED key 已写入 `.env`（2026-05-15 用户提供）。原先标 `⏸ 待 API key` 的项已全部解锁。

## P0 — MVP 骨架（让系统能跑）

- [x] (2026-05-15) git init + .gitignore + 首个 commit
- [x] (2026-05-15) 创建 requirements.txt（fredapi, pandas, requests, yfinance, flask, plotly, python-dotenv, pytest）
- [x] (2026-05-15) 创建 .env.example（FRED_API_KEY=, TZ=Asia/Shanghai）
- [x] (2026-05-15) src 目录加 __init__.py，建立模块边界（fetch / compute / store / web / utils）
- [x] (2026-05-15) src/utils/logger.py：统一 logging，输出到 logs/app.log + stdout
- [x] (2026-05-15) src/utils/config.py：从 .env 读配置，集中管理常量
- [x] (2026-05-15) src/store/db.py：SQLite 连接 + indicators 表 schema（id, name, date, value, source, ingested_at）
- [x] (2026-05-15) src/store/db.py：upsert_indicator(name, date, value, source) + get_latest(name) + get_series(name, days)
- [x] (2026-05-15) tests/test_db.py：覆盖 upsert / 查询 / 重复插入
- [x] (2026-05-15) src/fetch/fred_client.py：封装 fredapi，单方法 fetch_series(series_id, start)（同轮补完 tests/test_fetch.py 的 FRED 部分，5 个新用例）
- [x] (2026-05-15) src/fetch/yf_client.py：封装 yfinance，单方法 fetch_close(ticker, start)
- [x] (2026-05-15) tests/test_fetch.py：mock 外部，验证返回结构（yf_client + fred_client 全覆盖）
- [x] (2026-05-15) src/compute/thresholds.py：枚举三档（GREEN/YELLOW/RED）+ classify(value, low, high, direction) 通用函数
- [x] (2026-05-15) tests/test_thresholds.py：覆盖正向/反向/边界
- [x] (2026-05-15) 决策：P0 首条上线指标改用什么数据源 → 选 A：VIX via yfinance（DECISIONS.md 已记）。FRED 路径并行推进，等用户给 key 后开做
- [x] (2026-05-15) src/compute/indicators/vix.py：VIX（yfinance: ^VIX）实现 fetch+classify，写入 DB
- [x] (2026-05-15) tests/test_vix.py：mock yf_client，覆盖 fetch+classify+写库
- [x] (2026-05-15) src/compute/indicators/yield_curve.py：10Y-2Y（FRED: T10Y2Y）实现 fetch+classify
- [x] (2026-05-15) tests/test_yield_curve.py
- [x] (2026-05-15) src/web/app.py：Flask 起一页 / 路由 → 列出所有已实现指标，名/当前值/颜色/更新时间
- [x] (2026-05-15) templates/index.html：极简表格，颜色 inline style
- [x] (2026-05-15) scripts/daily_fetch.py：跑一遍所有已注册 fetcher，写入 DB
- [x] (2026-05-15) README 跑通指南：venv → pip → .env → daily_fetch → flask run，本地 http://localhost:5050 打开能看到 1 个指标
- [x] (2026-05-15) 用户验收里程碑：localhost:5050 看到第一条绿色/黄色指标 → VIX 17.26 GREEN（2026-05-14 收盘）

## P1 — 加指标（每个一轮，每个都包含 fetch + classify + 测试 + INDICATORS.md 翻译卡占位）

- [x] (2026-05-15) 10Y-3M（FRED: T10Y3M）— A 案阈值（与 10Y-2Y 同口径，DECISIONS.md 2026-05-15 ADR）
- [x] (2026-05-15) HY OAS（FRED: BAMLH0A0HYM2）— 阈值 GREEN<4 / YELLOW 4–8 / RED>8（DECISIONS.md 2026-05-15 ADR）
- [x] (2026-05-15) IG OAS（FRED: BAMLC0A0CM）— 阈值 GREEN<1.5 / YELLOW 1.5–3 / RED>3（DECISIONS.md 2026-05-15 ADR）
- [x] (2026-05-15) VIX 期限结构（VIX vs VIX3M / VIX6M）— 比值 ^VIX/^VIX3M 阈值 GREEN<0.95 / YELLOW 0.95–1.0 / RED>1.0
- [x] (2026-05-15) SOFR-IORB（FRED: SOFR - IORB）— |spread| bp，阈值 GREEN<5 / YELLOW 5–15 / RED>15
- [ ] FRA-OIS（代理序列）— ⏸ 决策点：LIBOR 退役后 FRA 已停发，FRED 无现成序列。候选代理待用户拍板
- [ ] Shiller PE（Robert Shiller 网站 CSV）— ⏸ 数据格式 .xls 需要 xlrd/openpyxl（不在白名单），触发暂停清单。可选绕路：multpl.com HTML 抓取（仅当前值，无历史）；或加白名单依赖。待用户拍
- [ ] Buffett Indicator（Wilshire 5000 / GDP）— ⏸ 决策点：FRED 有 WILL5000PRFC（日）和 GDP（季度），需要"日值 / 季度值前向填充"对齐逻辑。先确认是否值得做（季度 GDP 滞后 3 个月，作为崩盘监控敏感度低）
- [x] (2026-05-15) Dashboard 加分组：曲线 / 信用 / 估值 / 流动性 / 波动率 — 7 条指标分到 4 组，组 header 显示组内最严等级

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
