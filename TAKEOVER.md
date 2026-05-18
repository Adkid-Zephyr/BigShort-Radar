# BigShort Radar 交接手册

> 用户 lau 在 2026-05-18 早上做了一次完整迭代收尾,准备放下当前电脑/AI 助手,
> 让下一个接手的人(自己换电脑、或新助手)能够从零续上。
>
> 公开仓库 https://github.com/Adkid-Zephyr/BigShort-Radar
> 本地路径 /Users/lau/finance-radar/
> HEAD: `e09214d`(已 push)

---

## 一、5 分钟读懂这是什么

BigShort Radar 是 lau 个人的金融风险监控系统。**目的不是给所有人看的产品**,
是 lau 为自己**辅助交易**(沪深 300 期权 / 上证 50 期权 / 纳指期权 / 美股七姐妹个股期权)
而打造的"危机定价 + 大空头交易准备"实时温度计。

第一原则文档:
- `THESIS_PUBLIC.md` — 投资论点 / 5 个崩盘剧本 / 5 个反共识观察 / §6 缺失内容优先级
- `THESIS.md` — 私人版(gitignored,本机才有)

工作宪法:`PROMPT.md`

---

## 二、当前基线(HEAD e09214d,iter 57 完成)

| 维度 | 现状 |
|---|---|
| 测试 | pytest 504 通过 / 0 失败 / 0 skip |
| 指标 | 19 条 / 7 维度(波动率 / 曲线 / 信用 / 流动性 / 跨市场 / 政策 / 中国) |
| 综合温度计 | 7 维加权 + 维度内 max 触顶 + 切点 60 |
| Web | 7 page 全活:`/` `/events` `/heatmap` `/timeline` `/hedge` `/calibration` `/indicator/<name>` |
| 历史 cache | 38059 条 + 4 条原料(vix3m失败/sofr_raw 2027/iorb_raw 1755/dgs3mo 5096),覆盖 2006-2024 |
| 回测 | 三窗口 CSV 已出:2008 雷曼 / 2020 COVID / 2022 加息(`data/backtest_results/`) |
| 前端 | 信息驾驶舱方向,SVG 圆环 cockpit gauge + Bento 5 列 + 校准 stacked bar |

---

## 三、最近 3 轮做了什么(必看)

### iter 57(阈值校准 — 最近一轮)
解决 iter 52-54 三窗口回测发现"少数指标 RED 但综合分被稀释"盲区:
1. **派生指标回测现场计算**:`src/backtest/derived.py` 注册三条派生(vix_term_structure / sofr_iorb / fra_ois)的成分 + 公式;`backtest/score.py` 缺时调 derived;`backfill_history.py` 加 4 条原料
2. **维度内 max 触顶**:`risk_score.py::score_from_indicator_values` 把 mean 改 max
3. **切点 65→60**:配合 max 提高敏感度但避免"任一 YELLOW 就 RED"过敏感

三窗口重跑:2008 雷曼 RED 0→33 天 / COVID 0→42 天 / 2022 加息 39→393 天。
**残留盲区**:2022 持续 RED 占 72% 反映组间稀释(单组 100 加权后仅占 12-20% 份额);
VIX3M Yahoo 限速,vts 在回测仍 None。

### iter 56(前端二次美化)
信息驾驶舱方向:Bento 5 列单排 / 7 维度 2 列网格 / SVG 圆环 cockpit gauge / 校准 stacked bar。
截图归档 `.ralph/visual_iter56/`。

### iter 55(前端美化第一版)
taste-skill 规范深色精细化(Geist 字体 / liquid-glass shadow / Bento 非对称)。

---

## 四、用户对未来方向的明确表达(2026-05-18 早上)

> 我要辅助交易,可能交易沪深 300 期权 / 上证 50 期权 / 纳指期权 / 美股七姐妹个股期权。
> 有些期权或者专业交易员关注的数据也要追踪,然后把空的没有显示的数据也补齐一下。
> 如果需要我去找数据,那就告诉我。

详细缺口分析见 `.ralph/iter57_postmortem_pending.md`,核心几条:

### 当前 19 条指标的诚实评价

**真正有意义**(对期权交易直接有用):
- VIX / VIX 期限结构(决定 SPX/QQQ/七姐妹期权 IV 整体水平)
- HY OAS / IG OAS(比 VIX 反应快,信用→股票传导先行)
- DXY(对七姐妹海外营收影响巨大)
- USDJPY(科技股流动性踩踏尾部信号)
- VVIX / SKEW(期权交易者本职数据,但 yahoo 限速)
- 综合温度计 + 5 剧本(决定整体仓位敞口的"开关")

**对期权交易帮助有限**:
- 收益率曲线 10Y-2Y / 10Y-3M(对短期期权噪声大)
- 政策维度 WALCL / TGA / ON RRP(周值,对日内/周内不动)
- 中国外储 / CNY 10Y(月值滞后,对 A 股期权传导弱)
- SOFR-IORB / FRA-OIS(系统性极端才动,日常无用)

### 期权交易者真正盯,系统**完全没追踪**的数据
- Put/Call Ratio(CBOE total / equity / index)— 第一眼资金情绪
- IV Rank / Percentile(每条标的当前 IV 历史百分位)— 卖期权还是买期权的根本依据
- IV Skew(25-delta put - 25-delta call)
- IV Term Structure(每条标的自己的近月-远月)
- GEX(Gamma Exposure)— 决定标的当天 mean-revert 还是 trend
- 0DTE / 周期权占比 — 反身性核心,美股 50%+ 成交在 0DTE
- iVIX / iVX(中国波动率指数)
- 50ETF / 300ETF 期权 IV / Skew / PCR
- 北向 / 南向资金日数据
- 融资融券余额
- 股指期货升贴水(IH/IF/IC 基差)
- VIX9D / VIX1Y(超短超长波动率)— FRED 上有

### 当前 dashboard "暂无数据"的真实原因
- VIX(主流程)— yahoo `^VIX` 限速 → **应切 FRED:VIXCLS**(免费稳定,iter 58 候选第一)
- VIX 期限结构 — yahoo `^VIX3M` 限速 → 切 FRED:VXVCLS
- VVIX / SKEW — yahoo 限速;FRED 没有,需 CBOE 直拉 CSV
- SOFR-IORB / FRA-OIS — 主流程 daily_fetch 跑过应该有,需验证

### 数据源协助清单

**接手者自己能立即修(免费)**:
1. VIX 切 FRED:VIXCLS(一行代码)
2. VIX3M 切 FRED:VXVCLS(一行代码)
3. 加 VIX9D(FRED:VXSTCLS)、VIX1Y(FRED:VXMTCLS)
4. CBOE Put/Call Ratio 公开 daily CSV(`https://cdn.cboe.com/data/us/options/market_statistics/daily/`)— `requests` 已在依赖,不算新依赖
5. 联储票委鹰鸽指数(Atlanta Fed Hawk-Dove,FRED 上有 series)

**需要用户拍主意**:
- VVIX / SKEW 用 CBOE 直拉 CSV?(技术 OK,只是涉及"新 fetcher 路径"是否过于扩展)
- akshare 重启?(iter 38 决策方案 B 不引,但用户做沪深 300/上证 50 期权刚需)
- 七姐妹 IV/Skew 注册 ORATS/Tiingo Options?
- GEX(SqueezeMetrics 付费)?— 短期不做

---

## 五、暂停清单(命中立即写 BLOCKED.md 停)

- 引入 requirements.txt 之外的新依赖(**例外**:`requests` 已在 requirements,用 requests 拉 CBOE 公开 CSV 不算新依赖)
- 改 SQLite 表结构
- 改 INDICATORS.md 已定义指标口径或阈值(除非用户明确授权)
- 调付费 API
- 删除任何 .md 文件
- 单文件 > 300 行
- 连续两轮 pytest 没过
- 需要 FRED key / 百炼 key 之外的用户凭证
- **不引入 akshare**(iter 38 已决策方案 B,等用户重启)

---

## 六、跑环境

```bash
cd /Users/lau/finance-radar
# 启动 Flask
.venv/bin/python -m flask --app src.web.app run --host 127.0.0.1 --port 5050

# 跑 pytest
.venv/bin/python -m pytest -q

# 拉每日数据
.venv/bin/python -m scripts.daily_fetch

# backfill 历史
.venv/bin/python -m scripts.backfill_history --start 2020-01-01

# 跑回测
.venv/bin/python -m src.backtest.engine --start 2008-01-01 --end 2009-06-30 \
    --out data/backtest_results/lehman_2008.csv
```

依赖:
- Python 3.9 venv `.venv/`
- `.env` 含 FRED_API_KEY(本机才有,gitignored)
- 百炼 LLM key(可选,不影响主流程)

---

## 七、push 命令(token 走 gitignored 文件)

```bash
TOKEN=$(cat /Users/lau/finance-radar/.ralph/.token)
AUTH=$(printf "Adkid-Zephyr:%s" "$TOKEN" | base64)
git -c http.extraHeader="Authorization: Basic ${AUTH}" push origin main
```

**重要**:`.ralph/.token` 在 `.gitignore` 里,本机才有。GitHub secret scanning 会拦截
任何明文 token 进 commit。token:用户可在 GitHub Settings → Developer Settings 重生成。

---

## 八、ralph loop 状态(已暂停使用)

`scripts/ralph_loop.sh` 自动迭代脚本存在,但 2026-05-18 测试发现 nohup 后台模式
codebuddy 子进程**间歇性静默失败**(约 50% 概率 ~20 秒 exit=1 + 0 字节输出)。
未根因定位,可能与 codebuddy CLI 在无 tty 环境的 precheck 有关。

**白天有人在线时直接对话比 ralph loop 高效**,推荐保留 ralph loop 仅作"用户睡觉时尝试无人迭代"
的实验性工具,且每次启动后 30 分钟应人工检查一次进度。

可能的修复方向(未完成):
- 让 `ralph_loop.sh` 内的 codebuddy 调用加 `--output-format stream-json` + 实时 tee 监控
- 或改用 `tmux new-session -d` 在 detach session 里跑(有伪 tty)
- 或加重试包装:codebuddy 失败时间隔 30 秒重试 3 次

当前 `scripts/ralph_loop.sh` 仍是 stdin pipe 版,改文件重定向那次提交未保留(用户决定恢复干净)。

---

## 九、文件树速查

```
finance-radar/
├── THESIS_PUBLIC.md           # 第一原则(读这个,不读 THESIS.md)
├── PROMPT.md                  # 工作循环
├── HANDOFF.md                 # 接力手册(老的,本文件 TAKEOVER.md 是新的)
├── PLAN.md                    # 任务列表(顶项是当前要做的)
├── DECISIONS.md               # ADR 历史
├── INDICATORS.md              # 19 条指标的翻译卡(部分待用户输入)
├── README.md                  # 公开 GitHub README
├── TAKEOVER.md                # 本文件
│
├── src/
│   ├── compute/
│   │   ├── indicators/        # 19 条指标 fetch+classify 模块
│   │   ├── thresholds.py      # GREEN/YELLOW/RED Level
│   │   └── risk_score.py      # 综合温度计算法(iter 57 max + 切点 60)
│   ├── backtest/
│   │   ├── derived.py         # iter 57 派生指标现场计算
│   │   ├── engine.py          # 回测引擎
│   │   ├── score.py           # 单日打分(走 history cache)
│   │   ├── registry.py        # BACKTEST_INDICATORS(主+vix_fred+ted_spread)
│   │   └── report.py          # 三窗口 SUMMARY.md 生成
│   ├── store/
│   │   ├── db.py              # 主 DB(daily_fetch 写入)
│   │   └── history_db.py      # 历史 cache DB
│   ├── fetch/
│   │   ├── fred_client.py
│   │   ├── yf_client.py
│   │   └── history_fetcher.py # 多源 backfill
│   └── web/
│       ├── app.py             # Flask 路由 + _INDICATOR_REGISTRY
│       ├── charts.py          # plotly 详情页
│       ├── heatmap.py         # 风险矩阵 / 时间线
│       ├── hedge_calibration.py
│       ├── scenarios.py       # 5 剧本检测
│       ├── events.py          # 异常事件流
│       ├── sparkline.py
│       ├── zscore.py
│       ├── acceleration.py
│       └── comparisons.py     # 同环比
│
├── templates/                 # _base.html + 7 个页面 + indicator_detail
├── scripts/
│   ├── daily_fetch.py         # 每日跑所有 fetcher
│   ├── backfill_history.py    # 历史回填(--backtest 含扩展)
│   ├── ralph_loop.sh          # 自动迭代(暂不稳)
│   └── visual_check.sh        # 截图自检
├── tests/                     # 504 个用例
├── data/
│   ├── finance_radar.sqlite   # 主 DB(gitignored)
│   ├── historical_cache.sqlite # 历史 cache(gitignored)
│   └── backtest_results/      # CSV+SUMMARY(gitignored)
└── .ralph/
    ├── iteration.txt          # 当前迭代号(58)
    ├── last-summary.md        # 上一轮做了什么
    ├── progress.log           # 每轮一行历史
    ├── loop_prompt.md         # ralph loop 单轮 prompt
    ├── iter57_postmortem_pending.md  # 用户睡前留的方向
    └── visual_iter56/         # iter 56 截图
```

---

## 十、给接手者的建议

1. **先读 THESIS_PUBLIC.md + PROMPT.md + 本文件**,15 分钟够
2. **读完 last-summary.md + iter57_postmortem_pending.md** 知道用户最关心什么
3. **第一件事不要急着写代码** — 先跟用户对一次"现在最该做什么"
4. **保持客观自我评价** — 用户特别反感"自我满足式的完成",**先校准,再产品化**
5. **迭代风格**:一轮一件事,文档同步是基本职业素养,中文回复,不堆大段说明
6. **决策时给 2-4 个选项让用户挑**,不要自作主张

如果不确定下一步,直接问用户"现在走哪条"加 2-4 个选项,这是用户偏好的协作方式。
