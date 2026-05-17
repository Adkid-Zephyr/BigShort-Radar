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
- [x] (2026-05-17) empty 行（暂无数据）也保留 source 链接列展示（iter 36）— colspan=3 + 独立 source 列展示"查源"链接
- [x] (2026-05-17) GitHub 公开化推送 + README/THESIS 双份脱敏（iter 36）— public 仓库 `Adkid-Zephyr/BigShort-Radar`、CC BY-NC 4.0、`THESIS_PUBLIC.md` 脱敏版、`git filter-branch` 重写历史扫净 `THESIS.md`
- [x] (2026-05-17) README 文风重写为技术文档版（iter 37）— 去 emoji / 去营销词 / 一句话改事实陈述 / 17 个 H2 砍到合理结构 / 1500 字密度 / Roadmap 段写入 14 轮路线图

### 第二阶段路线图（iter 38–50，按用户 2026-05-17 拍板的"扩到 26 条 + 异常监测多视角 + 历史可视化"）

- [x] (2026-05-17) iter 38：历史数据 cache DB 骨架（**akshare 已拍板方案 B：不引入**，仅用 FRED+YF）— 新建 `data/historical_cache.sqlite` + `src/store/history_db.py` + `src/fetch/history_fetcher.py` + `scripts/backfill_history.py`，47 个新测试覆盖 cache DB CRUD + fetcher 路由 + backfill 脚本派生识别
- [x] (2026-05-17) iter 39：Sparkline 90 天微折线（首发异常监测视角）— `src/web/sparkline.py` 纯函数 SVG 渲染（折线 + 三档阈值带 + 末点高亮 + 数据不足"积累中"占位），`_INDICATOR_REGISTRY` 加 threshold/direction 元信息引用，`_build_rows` 注入 sparkline_svg，模板加"90 天"列。23 个新测试。8 条指标真实折线 + 2 条占位（VIX yahoo 限速 + SOFR-IORB 派生）
- [x] (2026-05-17) iter 40：Sparkline 可点击 + 指标详情页 + base.html 多页架构 — `templates/_base.html`（继承基础 + 顶部 nav）/ `templates/indicator_detail.html`（plotly 大图 + 元信息 dl）/ `src/web/charts.py`（plotly CDN，三档填色 + 阈值线 + 末点高亮）/ `app.py` 加 `/indicator/<name>` 路由 + REGISTRY_BY_NAME + `_fetch_history_pairs`。21 个新测试。详情页加载 plotly 3.5.0 CDN，HY OAS 等 786 数据点 5 年大图可缩放/拖动/导出 PNG
- [x] (2026-05-17) iter 41：同比 / 环比对比表 — `src/web/comparisons.py` 纯函数 `build_comparisons` 返 7d/30d/90d 三个 lookback 的 {value, pct_change, abs_change, deteriorate}（按 direction 判定），`_build_rows` 注入 comparisons 字段，模板加 3 列（红字=恶化绿字=改善），22 个新测试
- [ ] iter 42：5 年历史回填脚本跑一次 + Z-score 列 — 当前值在过去 5 年分布的位置（百分位）；VIX 改用 FRED:VIXCLS 替代 yahoo（避限速）
- [ ] iter 43：加速度（5/20 天斜率）列 — 标"突然变陡"的指标
- [ ] iter 44：政策反应维度 3 条 — WALCL（FRED:WALCL）/ ON RRP（FRED:RRPONTSYD）/ TGA（FRED:WTREGEN）
- [ ] iter 45：波动率结构 2 条 — VVIX（YF:^VVIX）/ SKEW（YF:^SKEW 或 CBOE）
- [ ] iter 46：FRA-OIS 代理（FRED 衍生：3M T-bill - SOFR）+ 中国维度骨架（FRED 系列）
- [ ] iter 47：中国维度 3 条上线 — 中国外汇储备（FRED:TRESEGCNM052N 月值）/ USDCNY 在岸（FRED:DEXCHUS）/ 中国 10Y（FRED:IRLTLT01CNM156N 月值）
- [ ] iter 48：异常事件流（30 天倒序）— 新页面 `/events`，列出"翻档 / 突破阈值 / 同时多指标走阔"的事件，用 base.html 与 nav
- [ ] iter 49：组合信号告警规则 — 5 个崩盘剧本检测器（剧本 A 美元荒 / B 国债基差 / C 日本 carry / D AI 泡沫 / E 信用滞后崩 各一条规则）
- [ ] iter 50：风险矩阵热力图 + 综合温度计 2 年时间线 — 新页面 `/heatmap` 与 `/timeline`
- [ ] iter 51：政策对冲对比页（视角 I）+ 阈值校准面板（视角 J）— 风险面 vs 对冲面 / 历史读数 vs 当时市场表现

**暂搁**（不在路线图，待评估）：
- 美元互换基差（USD basis swap）— 无免费源
- 国债基差交易杠杆（CFTC TFF 周报）— HTML 爬虫依赖暂停清单
- 美国 TIC 数据 — 财政部 HTML 同上
- 日本 30Y 国债 — FRED 无日值，OECD 月值且数据延迟
- akshare 中国维度 3 条（上证 PE / USDCNH 离岸 / 北向资金）— iter 38 决策方案 B 不引依赖暂搁；如未来用户重启需走单独 ADR

**总指标终态**：现 10 条 + 政策 3 + 波动率 2 + 融资 1 + 中国 3 = **19 条 / 7 维度**（原计划 26 条，方案 B 拍板后下调）

**历史回测框架**（THESIS §6.1，原最高优先）后置到 iter 51+，理由：用户拍板先扩指标 + 异常监测，再做回测。回测仍在路线图上。

### 历史归档（按 THESIS §6 排序，部分已被路线图覆盖）

#### 高优先（直接服务 THESIS 核心）

- [ ] 历史回测框架（THESIS §6.1）— 2007-08 / 2019-20 / 2022 加息套规则反向跑，看温度计在崩盘前 N 周读数曲线，校准权重与切点 — **路线图 iter 51+**
- [ ] z-score / 历史分位替换三档跳变（THESIS §6.2）— 量化粒度从 3 档 → 连续分布 — **路线图 iter 41**
- [ ] 加速度分量（THESIS §6.2）— 每条指标加"过去 N 天斜率"看变化方向 — **路线图 iter 42**
- [ ] 维度间用乘法叠加（THESIS §6.2）— "同时翻红"应该放大风险，不是被绿灯稀释 — **路线图 iter 48 联动**
- [ ] 组合信号检测（THESIS §6.2）— 多指标同时翻黄/红是真正的危机预警 — **路线图 iter 48**

#### 融资市场维度补缺（THESIS §4.3，08 真正引爆器）

- [ ] FRA-OIS 代理序列（USD3M T-bill - SOFR 或 GCF Repo - SOFR，待 ADR）— **路线图 iter 45**
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
- [x] (2026-05-17) GitHub 推送（iter 36）— public 仓库 `Adkid-Zephyr/BigShort-Radar`、CC BY-NC 4.0、THESIS.md 私有不进 git（filter-branch 清历史）、THESIS_PUBLIC.md 脱敏版进 repo、README 全量重写

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
