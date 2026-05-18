# BigShort Radar

[![tests](https://img.shields.io/badge/tests-504%20passed-brightgreen)](#测试)
[![python](https://img.shields.io/badge/python-3.9%2B-blue)](#技术栈)
[![license](https://img.shields.io/badge/license-CC%20BY--NC%204.0-orange)](./LICENSE)

本地金融风险监控系统。每天从 FRED / Yahoo Finance 拉 19 条宏观与市场指标，按预设阈值分档，七维加权生成 0–100 综合分，可选调用 LLM 出中文简报。
作者用它对抗自己的情绪化判断 —— 看历史指标，比看朋友圈靠谱。

完整投资论点见 [`THESIS_PUBLIC.md`](./THESIS_PUBLIC.md)（脱敏版）/ [`THESIS.md`](./THESIS.md)（私人版,private 仓库才有）。
**本项目不构成投资建议**，详见 [免责声明](#免责声明)。

---

## 🚀 新机快速上手(给接手者 / 给 AI 助手看)

**只需 GitHub 链接,就能让新机 + AI 自动配好。** AI 助手读完本节即知道要做什么、要找用户拿什么 key。

### Step 1 — clone + 看交接手册

```bash
git clone git@github.com:Adkid-Zephyr/BigShort-Radar.git finance-radar
cd finance-radar
```

接着按顺序读完(15 分钟):
1. [`TAKEOVER.md`](./TAKEOVER.md) — 30 秒上下文 + 用户对未来方向的明确表达
2. `THESIS_PUBLIC.md` — 第一原则
3. `PROMPT.md` — 工作宪法
4. `.ralph/last-summary.md` — 上一轮做了什么

### Step 2 — Key 清单(找用户拿)

| Key | 必填? | 用途 | 申请链接 | 不填会怎样 |
|---|---|---|---|---|
| `FRED_API_KEY` | **必填** | 拉 19 条指标里的 14 条(主力数据源) | https://fred.stlouisfed.org/docs/api/api_key.html (免费,1 分钟,只需注册邮箱) | 主流程几乎全废 |
| `DASHSCOPE_API_KEY` | 可选 | LLM 风险简报 + dashboard chatbot | https://bailian.console.aliyun.com/ (国内,需实名,有免费额度) | 简报 + chatbot 显示"未配置",其他不受影响 |
| GitHub PAT | 可选 | ralph_loop.sh 自动 push | GitHub Settings → Developer Settings → Personal access tokens(勾 `repo` scope) | ralph loop 跑完不会自动 push,需手动 push |

**AI 助手提示**:如果用户没现成的 FRED key,**直接告诉用户去申请,不要自己想办法绕开**。FRED 注册免费且 1 分钟搞定,这是项目主数据源,绕不过。

### Step 3 — 二选一:Docker 路径 / 传统 venv 路径

#### 路径 A: Docker(推荐 - 跨平台一致)

```bash
cp .env.example .env
# 编辑 .env,填入 Step 2 拿到的 FRED_API_KEY(其他可空)

docker-compose up -d                  # 启动 Flask,访问 http://localhost:5050
docker-compose logs -f radar          # 看日志

# 拉每日数据(主流程)
docker-compose run --rm radar python -m scripts.daily_fetch

# 回填历史(首次启动后)
docker-compose run --rm radar python -m scripts.backfill_history --start 2020-01-01

# 跑回测三窗口
docker-compose run --rm radar python -m src.backtest.engine --start 2008-01-01 --end 2009-06-30 --out data/backtest_results/lehman_2008.csv
```

#### 路径 B: 传统 venv(本机 Python 3.9.6)

```bash
cp .env.example .env
# 编辑 .env

python3.9 -m venv .venv               # 或 pyenv install 3.9.6 后 python -m venv
source .venv/bin/activate
pip install -r requirements.txt

# 启 Flask
python -m flask --app src.web.app run --host 127.0.0.1 --port 5050

# 跑 pytest 验证
python -m pytest -q                    # 期望 504 passed
```

### Step 4 — 数据现状(已 push,clone 后立刻可用)

仓库附带:
- `data/finance_radar.sqlite` — 主 DB(daily_fetch 累积)
- `data/historical_cache.sqlite` — 历史 cache(2006-2024,38059+ 条)
- `data/radar.sqlite` — 综合分历史
- `data/backtest_results/*.csv` — 三窗口回测结果(2008/COVID/2022)
- `THESIS.md` — 私人投资论点
- `.ralph/visual_iter56/` — iter 56 前端美化截图归档

clone 后**不用立刻**跑 backfill,数据已经在 git 里。但建议跑一次 `daily_fetch` 拿当天最新数据。

---

## 目录

- [架构](#架构)
- [指标](#指标)
- [综合温度计](#综合温度计)
- [Quickstart](#quickstart)
- [API key 申请](#api-key-申请)
- [LLM 集成](#llm-集成)
- [Dashboard](#dashboard)
- [自动化运行](#自动化运行)
- [Ralph Loop 自动迭代](#ralph-loop-自动迭代)
- [文件导览](#文件导览)
- [开发约定](#开发约定)
- [Roadmap](#roadmap)
- [技术栈](#技术栈)
- [测试](#测试)
- [License & 免责声明](#license)

## 架构

```
fetch/  ──►  compute/  ──►  store/  ──►  web/
FRED        thresholds      SQLite      Flask
yfinance    risk_score      (upsert,    + LLM
LLM         briefing        get_latest) dashboard
```

模块边界与目录约定见 [`ARCHITECTURE.md`](./ARCHITECTURE.md)。

## 指标

10 条 / 5 维度。每条的阈值依据见 [`INDICATORS.md`](./INDICATORS.md) 与 [`DECISIONS.md`](./DECISIONS.md)。

| 维度 | 指标 | 数据源 | 方向 | GREEN | YELLOW | RED |
|---|---|---|---|---|---|---|
| 波动率 | VIX | YF `^VIX` | up | < 20 | 20–30 | > 30 |
| 波动率 | VIX 期限结构（VIX/VIX3M） | YF `^VIX`÷`^VIX3M` | up | < 0.95 | 0.95–1.0 | > 1.0 |
| 曲线 | 10Y-2Y | FRED `T10Y2Y` | down | > 0.5 | 0–0.5 | < 0 |
| 曲线 | 10Y-3M | FRED `T10Y3M` | down | > 0.5 | 0–0.5 | < 0 |
| 信用 | HY OAS | FRED `BAMLH0A0HYM2` | up | < 4 | 4–8 | > 8 |
| 信用 | IG OAS | FRED `BAMLC0A0CM` | up | < 1.5 | 1.5–3 | > 3 |
| 流动性 | SOFR-IORB | FRED `SOFR`-`IORB` | up | < 5 bp | 5–15 bp | > 15 bp |
| 跨市场 | USDJPY | FRED `DEXJPUS` | up | < 145 | 145–160 | > 160 |
| 跨市场 | DXY 广义 | FRED `DTWEXBGS` | up | < 110 | 110–125 | > 125 |
| 跨市场 | 日本 10Y | FRED `IRLTLT01JPM156N` | up | < 1.0 | 1.0–2.0 | > 2.0 |

**阈值边界**：
- `up` 方向：`v == low` → GREEN；`v == high` → YELLOW；`v > high` → RED
- `down` 方向：`v == high` → GREEN；`v == low` → YELLOW；`v < low` → RED

## 综合温度计

```
Level → 分数：GREEN=0, YELLOW=50, RED=100
组内取算术平均 → 维度分
维度分 × 权重 → 总分
```

权重（合 100）：曲线 25 / 信用 25 / 跨市场 20 / 流动性 15 / 波动率 15
总分阈值：< 25 GREEN / 25–65 YELLOW / ≥ 65 RED

权重依据见 `DECISIONS.md` iter 29。算法将在 iter 41+ 升级（z-score、加速度、组合信号），见 [Roadmap](#roadmap)。

## Quickstart

```bash
git clone https://github.com/Adkid-Zephyr/BigShort-Radar.git
cd BigShort-Radar
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 填 FRED_API_KEY，可选 DASHSCOPE_API_KEY
python -m scripts.daily_fetch
python -m src.web.app  # http://localhost:5050
```

跑测试：`.venv/bin/pytest -q`

## API key 申请

**FRED**（必需，免费）：
1. <https://fred.stlouisfed.org/> 注册账号
2. <https://fred.stlouisfed.org/docs/api/api_key.html> 申请 key（"个人金融研究"用途，秒批）
3. 写入 `.env`：`FRED_API_KEY=<32 位字符串>`

**阿里百炼**（可选，付费）：缺失时 LLM 简报与 chatbot 自动降级，dashboard 仍可看。

```env
DASHSCOPE_API_KEY=sk-sp-...
DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
DASHSCOPE_MODEL=qwen3-coder-plus
```

`qwen-max` 在 Coding Plan endpoint 实测 400，必须用 `qwen3-coder-plus`。

## LLM 集成

模型：`qwen3-coder-plus`（OpenAI 兼容协议，仅用 `requests`，不引 SDK）。
两个使用点：

1. `src/compute/briefing.py` — 每天 launchd 跑完后生成约 250 字中文简报，写入 `briefings` 表
2. `/api/chat` — dashboard 浮窗，请求体附带最新指标快照作为 system prompt（避免 LLM 编造历史价位）

LLM 调用失败时 daily_fetch 主流程不受影响。

## Dashboard

Flask 单进程，端口 5050。包含：

- 综合温度计 gauge（大数字 + 颜色环）
- LLM 简报段（当日中文简报 + 时间 + 模型名）
- 5 维度分组，每组 header 显示组内最严等级
- 10 条指标行：名 + 当前值 + 等级 + 日期 + 可点击 source 链接（跳官方页）
- 右下角 chatbot 浮窗

## 自动化运行

macOS launchd：

```bash
bash scripts/install_launchd.sh install     # 装 + 启用
bash scripts/install_launchd.sh status      # 查状态
bash scripts/install_launchd.sh runonce     # 立即手动触发
bash scripts/install_launchd.sh uninstall
```

每天 05:30 (Asia/Shanghai) 触发 `scripts/daily_fetch.py`，日志在 `logs/launchd.{out,err}`。

非 macOS 用 cron：

```cron
30 5 * * * cd /path/to/BigShort-Radar && .venv/bin/python -m scripts.daily_fetch
```

## Ralph Loop 自动迭代

参考 [snarktank/ralph](https://github.com/snarktank/ralph)，结合本项目已有的 `PROMPT.md` / `PLAN.md` / `DECISIONS.md` 工作约定。

```bash
bash scripts/ralph_loop.sh 10
```

每轮启动新 codebuddy 进程，喂入 `.ralph/loop_prompt.md`。脚本兜底：BLOCKED.md 存在停 / pytest 红写 BLOCKED 停 / iteration.txt 没 +1 停。

完整说明见 `PROMPT.md` §"自动 loop 模式"。

视觉自检：`bash scripts/visual_check.sh` 起 Flask + chromium 截 dashboard 全图到 `.ralph/visual_check_iter<N>/`，agent 用 multimodal 看图。需先装 chromium：`playwright-cli install-browser chromium`（国内可能需代理）。

## 文件导览

```
THESIS_PUBLIC.md   投资论点（公开版）
PROMPT.md          工作宪法（5 步循环 / 8 条暂停清单 / 6 条文档同步纪律）
PLAN.md            任务列表
HANDOFF.md         接力手册
INDICATORS.md      指标说明书 + 阈值依据
ARCHITECTURE.md    架构与目录约定
DECISIONS.md       ADR 决策日志
.ralph/            自动迭代工作区
src/               代码
  fetch/           数据采集（fred/yf/llm）
  compute/         阈值 / 风险分 / 简报 / 各指标
  store/           SQLite 封装
  web/             Flask + source_links
  utils/           logger / config
scripts/           daily_fetch / ralph_loop / visual_check / launchd
templates/         dashboard 单文件模板
tests/             484 用例
```

## 开发约定

工作循环（每次"继续"跑一轮）：

1. 读 `PLAN.md` 顶项 `[ ]`、`.ralph/last-summary.md`、`.ralph/iteration.txt`
2. 检查 `BLOCKED.md`，存在则停
3. 写代码 → 写测试 → `pytest -q` 必须过
4. 文档同步 6 条检查：INDICATORS / DECISIONS / README / HANDOFF / THESIS / PLAN
5. PLAN `[ ]` → `[x] (YYYY-MM-DD)`，覆盖 last-summary，iteration +1，progress.log 追加一行
6. `git commit`，必要时 push

完整规范见 `PROMPT.md` 与 `HANDOFF.md`。

**必须暂停（写 BLOCKED.md，停）**：引入新依赖 / 改 SQLite schema / 改已定义指标阈值 / 调付费 API / 删 .md / 单文件 >300 行 / 连续两轮 pytest 红 / 需要新凭证。

## Roadmap

下一阶段（iter 37–50）按顺序执行：

| iter | 主题 |
|---|---|
| 37 | README 文风重写（本轮） |
| 38 | 历史数据 cache DB + akshare 引入 ADR |
| 39 | Sparkline 90 天微折线（每条指标右边） |
| 40 | 同比/环比对比表 |
| 41 | 5 年历史回填 + Z-score 列 |
| 42 | 加速度（5/20 天斜率）列 |
| 43 | 政策反应维度 3 条：WALCL / ON RRP / TGA |
| 44 | 波动率结构 2 条：VVIX / SKEW |
| 45 | FRA-OIS 代理 + 中国维度骨架 |
| 46 | 中国维度 6 条：外储 / 上证 PE / USDCNY / CNY 10Y / USDCNH / 北向资金 |
| 47 | 异常事件流（30 天倒序） |
| 48 | 组合信号告警规则（5 个崩盘剧本检测器） |
| 49 | 风险矩阵热力图 + 综合温度计 2 年时间线 |
| 50 | 政策对冲对比页 + 阈值校准面板 |

完成后总指标 26 条 / 7 维度，dashboard 含 sparkline / Z-score / 加速度 / 事件流 / 热力图 / 时间线 / 对冲面 / 校准面板。
路线图细节见 `PLAN.md` P3.6 段。

**iter 51 完成路线图终点**：实际方案 B 决策不引 akshare,总指标定型 19 条 / 7 维度。

**iter 52-54 历史回测**:跑通 2008 雷曼 / 2020 COVID / 2022 加息三窗口,关键发现"少数指标 RED 但综合分被稀释"模式 — 需要 iter 57 阈值校准修正。

**iter 55-56 前端美化两轮**:iter 55 用 taste-skill 规范做深色精细化,iter 56 改信息驾驶舱方向(SVG 圆环 cockpit gauge + 7 维度径向条 + Bento 5 列单排 + 校准 stacked bar)。详见 `DECISIONS.md` iter 55-56。

**iter 57 阈值校准**:派生指标 vix_term_structure / sofr_iorb / fra_ois 在回测时用底层成分现场计算(消除三窗口 100% missing);维度内 max 触顶(任一指标 RED → 维度 100,解决"少数指标 RED 但综合分被稀释"盲区);总分切点 65→60。三窗口重跑:2008 雷曼 RED 33 天 / COVID 42 天 / 2022 加息 393 天(过去仅 0/0/39)。pytest 504。

## 技术栈

- Python 3.9+
- 依赖白名单（`requirements.txt`）：`fredapi pandas requests yfinance flask plotly python-dotenv pytest`
- SQLite 单文件（`data/radar.sqlite`）
- Flask 5050 端口
- pytest，外部库一律 mock，不打真实网络

## 测试

```bash
.venv/bin/pytest -q
```

当前 484 用例 / 0 失败 / 0 skip。每个 src 模块至少一个测试。Web 测试用 Flask `test_client` + tmp SQLite。

## License

[CC BY-NC 4.0](./LICENSE) — 允许学习、修改、非商业分享，禁止商业使用。

## 免责声明

本项目是个人工具，不构成投资建议。指标阈值由作者基于公开历史数据和文献设定，可能存在偏差或过时。
任何使用本项目代码、数据、文档进行决策的读者，需自行判断、自行承担风险。
作者不对任何因使用本项目导致的财务损失承担责任。
