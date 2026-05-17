# PLAN

> 工作约定：每轮只做最上面一个 `[ ]`。完成后改成 `[x] (YYYY-MM-DD)`。
> 任务粒度需控制在单轮 30 分钟内完成；过粗的先拆。
>
> **优先级原则**：所有任务先回头看 `THESIS.md` §6 "还需要在系统中体现的、当前缺失的内容"。
> 与 THESIS 优先级冲突时以 THESIS 为准。
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

## P3 — 解读层 & 综合温度计（已完成基础三件套）

- [x] (2026-05-15) LLM 接入：阿里百炼 Coding Plan + 每日风险简报 + dashboard 顶部渲染（DECISIONS.md iter 27 ADR）
- [x] (2026-05-15) 综合温度计：五维度加权 → 单一风险分（0-100）— iter 29，权重曲线 25 / 信用 25 / 跨市场 20 / 流动性 15 / 波动率 15
- [x] (2026-05-15) /chat 对话接口：用户能就当前指标向 LLM 追问 — iter 30，浮窗 UI + /api/chat POST
- [x] (2026-05-17) THESIS.md 投资论点文档化（iter 33）— 第一原则文档，与 PROMPT/HANDOFF/README 同步

## P3.5 — 日本与跨市场维度（崩盘剧本必备，THESIS §3.2 剧本 C）

- [x] (2026-05-15) USDJPY（FRED:DEXJPUS）— carry trade 解除信号，阈值 145/160
- [x] (2026-05-15) DXY 美元广义指数（FRED:DTWEXBGS）— 美元强弱反向交叉，阈值 110/125
- [x] (2026-05-15) 日本 10Y 国债收益率（FRED:IRLTLT01JPM156N 月值）— YCC 退出后真正爆点，阈值 1.0/2.0

## P3.6 — 用户 2026-05-17 反馈后的真实优先级（按 THESIS §6 排序）

> 用户认为：当前三档加权"不客观、不管用"，前端不直观，且 THESIS 之前缺失。
> 这是项目从"MVP 收官"进入"科学校准"阶段的真实清单。

### 工程化基础设施

- [x] (2026-05-17) ralph loop 脚手架（iter 34a）— `scripts/ralph_loop.sh` + `.ralph/loop_prompt.md` + `.ralph/progress.log`，支持自动连续跑 N 轮，兜底 pytest/BLOCKED/iter 校验
- [x] (2026-05-17) ralph loop multimodal 自检（iter 34b）— `scripts/visual_check.sh` + `.ralph/visual_check_template.md` + loop_prompt §4.5。前端改动后跑 visual_check 截图，agent 用 Read 看图自检，写 `.ralph/visual_check_iter<N>.md`。chromium 浏览器需用户首次装（国内代理）
- [x] (2026-05-17) 指标 source 列改成可点击官方页外链（iter 35）— `src/web/source_links.py` FRED/YF/OECD/CBOE 前缀映射 + registry `source_url` 字段优先，模板蓝色 anchor + ↗ 箭头 + 新页签
- [ ] empty 行（暂无数据）也保留 source 链接列展示 — 现 colspan=4 占位把链接吞了，让用户没数据时也能跳官方页查

### 高优先（直接服务 THESIS 核心）

- [ ] 历史回测框架（THESIS §6.1）— 2007-08 / 2019-20 / 2022 加息套规则反向跑，看温度计在崩盘前 N 周读数曲线，校准权重与切点
- [ ] z-score / 历史分位替换三档跳变（THESIS §6.2）— 量化粒度从 3 档 → 连续分布
- [ ] 加速度分量（THESIS §6.2）— 每条指标加"过去 N 天斜率"看变化方向
- [ ] 维度间用乘法叠加（THESIS §6.2）— "同时翻红"应该放大风险，不是被绿灯稀释
- [ ] 组合信号检测（THESIS §6.2）— 多指标同时翻黄/红是真正的危机预警

### 融资市场维度补缺（THESIS §4.3，08 真正引爆器）

- [ ] FRA-OIS 代理序列（USD3M T-bill - SOFR 或 GCF Repo - SOFR，待 ADR）
- [ ] 美元互换基差（USD basis swap）— 离岸美元短缺
- [ ] 国债基差交易杠杆（CFTC TFF 周报）— IMF/BIS 警告但被低估

### 政策反应维度（THESIS §4.1 揭示的盲区）

- [ ] 联储资产负债表方向（FRED:WALCL）— QE/QT 直接信号
- [ ] TGA 余额（财政部一般账户）— 财政部弹药
- [ ] ON RRP 余额 — 流动性下限框架

### 波动率结构补全（THESIS §4.2 反身性）

- [ ] SKEW 指数（CBOE）
- [ ] VVIX
- [ ] 0DTE 期权占比监控

### 跨市场补全（THESIS §4.4 三角联动）

- [ ] 日本 30Y 国债收益率（超长端是真正爆点）
- [ ] BoJ 资产规模 YoY 派生指标
- [ ] 中国外汇储备月度
- [ ] 美国 TIC 数据

### 前端可视化升级（THESIS §6.7）

- [ ] 每条指标 90 天 sparkline + 阈值带
- [ ] z-score 在历史分布上的位置可视化
- [ ] 风险矩阵热力图（横轴日期 × 纵轴指标，看"同时翻红"）
- [ ] 综合温度计 2 年时间线

### 仓位建议输出（THESIS §5.3，连接监控到行动）

- [ ] 综合分 → 风险敞口/对冲预算/现金 映射表代码化
- [ ] 简报追加"建议仓位敞口 X% / 对冲预算 Y%"

### 失效条件（THESIS §6.9）

- [ ] 6 个月跑下来后回看：阈值是否过敏感/过迟钝
- [ ] 假设证伪机制：方向错就承认 + 调整 + 必要时关闭

### 长期未做（保留）

- [ ] INDICATORS.md 每个指标补足"翻译卡"（含义/误判/历史案例）— 等用户输入
- [ ] 估值维度补缺（Shiller PE 因 .xls 依赖暂搁、Buffett Indicator 季度滞后暂搁，需替代代理）

## P4 — 自动化与运维

- [x] (2026-05-15) launchd plist：每天美东 16:30 ≈ 北京 05:30 触发 daily_fetch — iter 31，scripts/install_launchd.sh 一键装/卸/查
- [ ] 失败重试 + 日志轮转
- [ ] 数据缺失告警（连续 N 天没拿到 → 邮件/飞书）
- [ ] 备份脚本：每日 sqlite 拷贝到 ~/Backups/

## P4.5 — 产品化

- [x] (2026-05-15) README 完整化：启动指南、launchd 安装、API key 申请、维度阈值一览表 — iter 32
- [ ] GitHub 推送（待用户拍 4 项决策：可见性 / 账号 / 仓库名 / License）

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
