# BigShort Radar

> 本地金融风险监控系统：每日采集宏观与市场指标，按维度加权算综合"风险温度计"，
> 用 LLM 生成中文简报，并支持基于真实数据的对话式追问。
>
> **不预测崩盘 · 不给买卖时点 · 不构成投资建议**
> 它是一份让你**在风险持续累积期活得够久、当尾部事件真正发生时不缺席**的纪律工具。

[![tests](https://img.shields.io/badge/tests-197%20passed-brightgreen)](#测试)
[![python](https://img.shields.io/badge/python-3.9%2B-blue)](#技术栈)
[![license](https://img.shields.io/badge/license-CC%20BY--NC%204.0-orange)](./LICENSE)

---

## 目录

- [一句话定位](#一句话定位)
- [它能做什么 / 不做什么](#它能做什么--不做什么)
- [项目当前进度（v33 已完成内容快照）](#项目当前进度v33-已完成内容快照)
- [架构总览](#架构总览)
- [10 条核心指标 · 5 个维度](#10-条核心指标--5-个维度)
- [综合风险温度计](#综合风险温度计)
- [LLM 集成](#llm-集成)
- [Web Dashboard](#web-dashboard)
- [自动化运行（macOS launchd）](#自动化运行macos-launchd)
- [Ralph Loop 自动迭代开发](#ralph-loop-自动迭代开发)
- [Multimodal 视觉自检](#multimodal-视觉自检)
- [一分钟启动](#一分钟启动)
- [API Key 申请](#api-key-申请)
- [项目文件导览](#项目文件导览)
- [开发约定](#开发约定)
- [接下来的路线（按优先级）](#接下来的路线按优先级)
- [License](#license)
- [免责声明](#免责声明)

---

## 一句话定位

> **认知工具 + 仓位调节器 + 认知输出原料库**

把 10 条分散的宏观信号每日聚合成 0–100 的综合分，配中文简报和可追问的助手，对抗自己的情绪化判断。完整投资论点见 [`THESIS_PUBLIC.md`](./THESIS_PUBLIC.md)。

## 它能做什么 / 不做什么

✅ **能做**

- 每天自动从 FRED / Yahoo Finance 拉 10 条宏观与市场指标
- 把每条指标按预设阈值分到 GREEN（平静）/ YELLOW（紧张）/ RED（危机定价）
- 把 5 维度按权重聚合成 0–100 综合分，分三档颜色
- 生成中文风险简报（约 250 字，基于当天真实数据）
- 提供浏览器 dashboard + 浮窗 chatbot（基于真实快照向 LLM 追问）
- launchd 每日 05:30 自动跑（≈ 美东收盘后半小时）
- 任何指标点击即跳官方页（FRED series 页 / Yahoo quote 页 / CBOE 规格页）

❌ **明确不做**

- 不做实时分钟级行情
- 不做交易执行（信号系统不是下单系统）
- 不做账户聚合 / 仓位管理
- 不预测精确崩盘时点（"明天空"这种判断 = 红灯心态）
- 不引入 ORM、消息队列、容器（MVP 简化优先）

## 项目当前进度（v33 已完成内容快照）

- ✅ MVP 骨架（fetch / store / compute / web / utils 五大模块）
- ✅ SQLite + 通用 upsert 抽象
- ✅ 通用阈值分类器（up / down 方向 + 边界规则）
- ✅ 10 条指标全部上线（5 维度）
- ✅ 综合风险温度计（五维加权 25/25/20/15/15）
- ✅ Flask dashboard（分组 + 颜色 + 总分大数字 gauge）
- ✅ LLM 集成（阿里百炼 qwen3-coder-plus）
- ✅ /api/chat 浮窗对话接口（系统 prompt 含真实数据快照）
- ✅ launchd 每日 05:30 自动跑
- ✅ 任何指标点击 source 列跳官方页
- ✅ 投资论点 THESIS_PUBLIC.md 文档化
- ✅ Ralph Loop 自动迭代脚本 + Multimodal 视觉自检脚本
- ✅ 197 用例 / 0 失败 / 0 skip

进度详情见 [`PLAN.md`](./PLAN.md)、[`DECISIONS.md`](./DECISIONS.md)、[`.ralph/progress.log`](./.ralph/progress.log)。

## 架构总览

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  fetch/      │───►│  compute/    │───►│  store/      │───►│  web/        │
│  FRED, YF,   │    │  thresholds, │    │  SQLite      │    │  Flask, LLM  │
│  LLM client  │    │  risk_score, │    │  (upsert,    │    │  dashboard   │
│              │    │  briefing    │    │  get_latest) │    │  + chatbot   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
        ▲                                       ▲                    ▲
        │                                       │                    │
   .env (FRED key,                       data/radar.sqlite      browser
   DASHSCOPE key)                        (本地，不进 git)        :5050
```

模块边界与目录约定见 [`ARCHITECTURE.md`](./ARCHITECTURE.md)。

## 10 条核心指标 · 5 个维度

| 维度 | 指标 | 数据源 | 方向 | GREEN | YELLOW | RED |
|---|---|---|---|---|---|---|
| **波动率** | VIX 恐慌指数 | YF `^VIX` | up | < 20 | 20–30 | > 30 |
| **波动率** | VIX 期限结构（VIX/VIX3M） | YF `^VIX`÷`^VIX3M` | up | < 0.95 | 0.95–1.0 | > 1.0 |
| **曲线** | 10Y-2Y 收益率曲线 | FRED `T10Y2Y` | down | > 0.5 | 0–0.5 | < 0 |
| **曲线** | 10Y-3M 收益率曲线 | FRED `T10Y3M` | down | > 0.5 | 0–0.5 | < 0 |
| **信用** | HY OAS 高收益债利差 | FRED `BAMLH0A0HYM2` | up | < 4 | 4–8 | > 8 |
| **信用** | IG OAS 投资级利差 | FRED `BAMLC0A0CM` | up | < 1.5 | 1.5–3 | > 3 |
| **流动性** | SOFR-IORB | FRED `SOFR`-`IORB` | up | < 5 bp | 5–15 bp | > 15 bp |
| **跨市场** | USDJPY 美元日元 | FRED `DEXJPUS` | up | < 145 | 145–160 | > 160 |
| **跨市场** | DXY 美元广义指数 | FRED `DTWEXBGS` | up | < 110 | 110–125 | > 125 |
| **跨市场** | 日本 10Y 国债收益率 | FRED `IRLTLT01JPM156N` | up | < 1.0 | 1.0–2.0 | > 2.0 |

每条指标的阈值依据、历史分位、数据源说明见 [`INDICATORS.md`](./INDICATORS.md) 和 [`DECISIONS.md`](./DECISIONS.md)。

**阈值边界规则**（见 `DECISIONS.md` 2026-05-15）：
- `up` 方向：`v == low` → GREEN；`v == high` → YELLOW；`v > high` → RED
- `down` 方向：`v == high` → GREEN；`v == low` → YELLOW；`v < low` → RED

## 综合风险温度计

```
每条指标按 Level 转分：GREEN=0 / YELLOW=50 / RED=100
同 group 内取算术平均 → 维度分
维度分 × 维度权重 → 总分
```

**维度权重**（合 100，依据见 `DECISIONS.md` iter 29）：

| 维度 | 权重 | 理由 |
|---|---|---|
| 曲线 | 25% | 衰退最强先行（10Y-2Y 倒挂后 ~14 个月触发衰退） |
| 信用 | 25% | 危机定价最快反应 |
| 跨市场 | 20% | 抓 2025-26 主剧本（日元 carry / 强美元） |
| 流动性 | 15% | 危机引爆器但平时低噪 |
| 波动率 | 15% | VIX 偶尔失灵，弱权重 |

**总分阈值**：< 25 GREEN / 25–65 YELLOW / ≥ 65 RED

**未来要做的算法升级**（见 `THESIS_PUBLIC.md` §6.2 与 `PLAN.md` P3.6）：
- z-score / 历史分位替换三档跳变
- 维度间用乘法叠加（同时翻红 → 风险放大）
- 加入加速度分量（过去 N 天斜率）
- 组合信号检测（多指标同时翻黄/红）

## LLM 集成

**模型**：`qwen3-coder-plus`（阿里百炼 Coding Plan，OpenAI 兼容协议）
**Endpoint**：`https://coding.dashscope.aliyuncs.com/v1`
**调用方**：`src/fetch/llm_client.py` —— 仅用 `requests`，不引 SDK

**两个使用场景**：

1. **每日风险简报**（`src/compute/briefing.py`）
   每天 launchd 跑完 fetch 后自动调一次：拼当日所有指标 + 综合分 → LLM 出约 250 字中文简报 → 写入 `briefings` 表 → dashboard 顶部展示

2. **Chatbot 浮窗对话**（`/api/chat`）
   用户在 dashboard 浮窗里向 LLM 追问，请求体附带最新指标快照作为 system prompt（不让 LLM 编造历史价位）

**优雅降级**：DASHSCOPE_API_KEY 缺失或 LLM 调用失败时，daily_fetch 主流程不受影响，简报字段空着，dashboard 照常工作。

## Web Dashboard

**端口**：`5050`（避开常用 5000）
**起法**：`python -m src.web.app` 或 `.venv/bin/python -m src.web.app`
**访问**：<http://localhost:5050/>

**包含元素**：

- 顶部综合风险温度计 gauge：大数字 0–100 + 颜色环 + 三档色带
- LLM 简报段：当日中文简报 + 生成时间 + 模型名
- 5 个维度分组：每组 header 显示组内最严等级颜色
- 10 条指标行：名 + 当前值 + 等级 + 日期 + **可点击 source 链接（跳官方页）**
- 右下角 chatbot 浮窗按钮：基于真实快照与 LLM 对话
- 底部 legend：颜色含义说明

**技术栈**：Flask + Jinja2 + 原生 CSS + 极少 JS（chatbot 浮窗）。无前端框架、无 React、无 Vue。

## 自动化运行（macOS launchd）

```bash
bash scripts/install_launchd.sh install     # 装 + 启用
bash scripts/install_launchd.sh status      # 看运行状态
bash scripts/install_launchd.sh runonce     # 立即手动触发一次
bash scripts/install_launchd.sh uninstall   # 卸载
```

- 触发时间：每天 **05:30 (Asia/Shanghai)**，约美东收盘后半小时
- 跑的是：`scripts/daily_fetch.py`（顺序拉所有指标 → 入库 → 算综合分 → 调 LLM 出简报）
- 日志：`logs/launchd.out` 与 `logs/launchd.err`
- plist：`scripts/com.financeradar.daily.plist`

非 macOS 用户可以用 cron 自己写一行：

```cron
30 5 * * * cd /path/to/BigShort-Radar && .venv/bin/python -m scripts.daily_fetch
```

## Ralph Loop 自动迭代开发

参考了 [snarktank/ralph](https://github.com/snarktank/ralph) 的"主循环 + 全新上下文 + 跨轮记忆"思想，结合本项目已有的 `PROMPT.md` / `PLAN.md` / `DECISIONS.md` 工作约定整合：

```bash
bash scripts/ralph_loop.sh 10           # 自动连跑 10 轮
bash scripts/ralph_loop.sh 5 --dry-run  # 联调用，不真启动 codebuddy
```

**机制**：每轮启动一个**全新** codebuddy 进程，喂入 `.ralph/loop_prompt.md`，由全新上下文的 agent 自己读 8 文件 + 跑工作循环 5 步。脚本兜底校验：

| 校验 | 不通过 → 行为 |
|---|---|
| `BLOCKED.md` 存在 | 立刻停 |
| `pytest -q` 红 | 写 BLOCKED.md 停 |
| `.ralph/iteration.txt` 没 +1 | 视为本轮没收尾，停 |

**与 ralph 原版的关键差异**：

| 维度 | ralph 原版 | 本项目 |
|---|---|---|
| 任务源 | `prd.json` 故事列表 | `PLAN.md` 顶项 `[ ]` |
| 跨轮记忆 | `progress.txt` 追加 + AGENTS.md | `last-summary.md` 覆盖 + `progress.log` 追加 + ADR |
| 暂停 | 标 fail 跳过 | `BLOCKED.md` 主动停 |
| 单轮预算 | typecheck + tests | `--max-turns 80` + pytest |

完整说明见 `PROMPT.md` §"自动 loop 模式"。

## Multimodal 视觉自检

ralph loop 防"agent 写完代码自吹自擂"的最后一道防线：

```bash
bash scripts/visual_check.sh           # 自起 Flask 截图
bash scripts/visual_check.sh --no-flask  # Flask 已起则复用
```

输出到 `.ralph/visual_check_iter<N>/`：
- `dashboard.png` — 1440×900 全页截图（chromium）
- `dom.yaml` — 结构化 DOM 快照
- `console.txt` — JS console 日志
- `flask.log` — Flask 输出

然后 agent 用 `Read` 工具加载截图，按 `.ralph/visual_check_template.md` 6 段（改动摘要 / 自检命令 / 必查项 / 看图问题 / 结论 / TODO）填 `.ralph/visual_check_iter<N>.md`。

**首次需装 chromium**：

```bash
playwright-cli install-browser chromium
# 国内可能需 HTTPS_PROXY 或 PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
```

`scripts/visual_check.sh` 检测不到浏览器会 graceful 退出 + 给指引，不会卡死。

## 一分钟启动

```bash
git clone https://github.com/Adkid-Zephyr/BigShort-Radar.git
cd BigShort-Radar

# 1. 建虚拟环境
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 配置 .env
cp .env.example .env
# 编辑 .env，填入：
#   FRED_API_KEY=你的key                 # 必需，免费注册
#   DASHSCOPE_API_KEY=sk-sp-...          # 可选，缺失时 LLM 功能降级
#   DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
#   DASHSCOPE_MODEL=qwen3-coder-plus

# 3. 拉数据（首次几秒钟）
python -m scripts.daily_fetch

# 4. 起 dashboard
python -m src.web.app
# 浏览器打开 http://localhost:5050
```

跑测试：

```bash
.venv/bin/pytest -q
```

## API Key 申请

### FRED（必需 · 免费）

1. 打开 <https://fred.stlouisfed.org/>
2. 右上 **My Account** → **Register** → 邮箱验证
3. 进 <https://fred.stlouisfed.org/docs/api/api_key.html> → **Request API Key**，"个人金融研究"用途，秒批
4. 32 位字符串写到 `.env`：`FRED_API_KEY=...`

### 阿里百炼（可选 · 付费）

LLM 简报与 chatbot 用。**缺失时这两个功能自动降级**（dashboard 仍可看，每日数据照常入库）。

1. <https://bailian.console.aliyun.com/> 开通 Coding Plan
2. 拿 API Key（`sk-sp-` 开头），写到 `.env`：
   ```
   DASHSCOPE_API_KEY=sk-sp-...
   DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
   DASHSCOPE_MODEL=qwen3-coder-plus
   ```

实测 `qwen-max` 在 Coding Plan endpoint 不支持，必须用 `qwen3-coder-plus`。

## 项目文件导览

### 根目录文档

| 文件 | 用途 |
|---|---|
| [`THESIS_PUBLIC.md`](./THESIS_PUBLIC.md) | **第一原则（公开版）** — 投资论点 / 5 个崩盘剧本 / 5 个反共识观察 / 9 类缺失内容优先级 |
| [`PROMPT.md`](./PROMPT.md) | Vibe coding 工作宪法：5 步循环 / 8 条暂停清单 / 6 条文档同步纪律 / 自动 loop 模式 |
| [`PLAN.md`](./PLAN.md) | 任务列表 — 顶项 `[ ]` 即下一轮要做的事，做完打 `[x] (YYYY-MM-DD)` |
| [`HANDOFF.md`](./HANDOFF.md) | 接力手册：30 秒上下文 / 必读清单 / 跑环境 / 关键约定 / 留痕规范 |
| [`INDICATORS.md`](./INDICATORS.md) | 指标说明书 + 阈值依据 + 翻译卡（含义/误判/历史案例，由作者手写） |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | 模块边界与数据流 |
| [`DECISIONS.md`](./DECISIONS.md) | ADR 风格决策日志（架构 / 选型 / 阈值 / 算法 / 流程） |
| [`README.md`](./README.md) | 你正在看的这份 |
| [`LICENSE`](./LICENSE) | CC BY-NC 4.0 |

### Ralph 工作区

| 文件 | 用途 |
|---|---|
| `.ralph/loop_prompt.md` | 自动循环单轮 prompt 模板 |
| `.ralph/last-summary.md` | 上一轮做了什么 + 下一轮建议（**覆盖式**） |
| `.ralph/progress.log` | 每轮一行历史（**追加式**） |
| `.ralph/visual_check_template.md` | 视觉自检报告模板 |
| `.ralph/iteration.txt` | 当前迭代号（gitignore，本地维护） |

### 代码

```
src/
├── fetch/        # 数据采集（fred_client / yf_client / llm_client）
├── compute/      # 计算逻辑
│   ├── thresholds.py       # 通用 GREEN/YELLOW/RED 分类器
│   ├── risk_score.py       # 综合温度计加权算法
│   ├── briefing.py         # LLM 简报生成
│   └── indicators/         # 10 条指标各自的 fetch + classify 逻辑
├── store/        # SQLite 封装（upsert_indicator / get_latest / 通用 upsert_series_from_pandas）
├── web/          # Flask 应用
│   ├── app.py              # 路由 + 注册表 + 渲染
│   └── source_links.py     # 指标 source → 官方页 URL 映射
└── utils/        # logger / config

scripts/
├── daily_fetch.py          # 每日跑一遍所有指标 + 综合分 + LLM 简报
├── ralph_loop.sh           # 自动迭代主循环
├── visual_check.sh         # Multimodal 视觉自检
├── install_launchd.sh      # macOS launchd 一键装/卸/查
└── com.financeradar.daily.plist

tests/   # 198 用例 / 0 失败 / 0 skip
templates/index.html        # dashboard 单文件模板
```

## 开发约定

任何新 agent / 新设备打开仓库后：

1. 先读 `HANDOFF.md`（30 秒上下文）+ `THESIS_PUBLIC.md`（第一原则）+ `PROMPT.md`（工作宪法）
2. 跑 `.venv/bin/pytest -q` 确认基线绿
3. 看 `.ralph/last-summary.md` 知道上一轮做到哪
4. 找 `PLAN.md` 顶上的第一个 `[ ]`，按 `PROMPT.md` 工作循环跑一轮
5. 收尾必做：测试通过 + 打勾 + commit + 更新 last-summary + iteration+1 + progress.log 追加一行
6. **文档同步纪律**（每轮强制）：代码改完后过 6 条检查清单——INDICATORS / DECISIONS / README / HANDOFF / THESIS / PLAN，逐条问"我刚才的改动影响了它吗"

详见 `HANDOFF.md` §6 留痕规范、`PROMPT.md` 工作循环、`DECISIONS.md` "重复三次再抽象"等历史决策。

### 必须暂停清单（命中就写 BLOCKED.md，停）

- 引入 `requirements.txt` 之外的新依赖
- 改 SQLite 表结构
- 改 INDICATORS.md 已定义指标口径或阈值（除非用户明确授权）
- 调用付费 API
- 删除任何 `.md` 文件
- 单文件即将 >300 行
- 连续两轮 pytest 没过
- 需要 FRED / 百炼 key 之外的用户凭证

## 接下来的路线（按优先级）

按 `THESIS_PUBLIC.md` §6 排序：

1. **历史回测框架**（最高优先）—— 2007-08 / 2019-20 / 2022 加息真实数据反向跑当前阈值与温度计，校准权重与切点
2. **z-score / 历史分位** 替换三档跳变
3. **加速度分量**（过去 N 天斜率）
4. **维度间乘法叠加 + 组合信号检测**
5. **融资市场维度补缺**：FRA-OIS、USD basis swap、国债基差杠杆估算
6. **政策反应维度**：WALCL、TGA、ON RRP（看"对冲面"）
7. **波动率结构补全**：SKEW、VVIX、0DTE 占比
8. **跨市场补全**：日本 30Y、中国外储、美国 TIC
9. **前端可视化升级**：sparkline、z-score 位置、风险矩阵热力图、温度计 2 年时间线
10. **仓位建议输出**：把综合分映射到风险敞口/对冲预算/现金比例
11. **失效条件**：6 个月后回看是否过敏感/过迟钝，方向错就承认 + 调整或关闭

## 技术栈

- **Python 3.9+**（系统兼容性优先）
- **依赖白名单**（`requirements.txt`）：`fredapi pandas requests yfinance flask plotly python-dotenv pytest`
- **数据库**：SQLite（单文件 `data/radar.sqlite`，零运维；MVP 量级够用）
- **Web**：Flask 单进程 5050 端口
- **测试**：pytest，每个 src 模块至少一个测试，所有外部库 mock
- **LLM**：阿里百炼 OpenAI 兼容协议，仅 `requests` 不引 SDK

## 测试

```bash
.venv/bin/pytest -q
```

当前：**197 用例 / 0 失败 / 0 skip**

测试规范：
- 测试文件 `tests/test_*.py`，每个 src 模块至少一个测试
- 所有外部库（fredapi / yfinance / requests）必须 mock，不打真实网络
- Web 测试用 Flask `test_client` + tmp SQLite，不依赖真实 dashboard

## License

[CC BY-NC 4.0](./LICENSE) —— 允许学习、修改、非商业分享，禁止商业使用。

## 免责声明

本项目是个人工具，**不构成投资建议**。指标阈值由作者基于公开历史数据和文献设定，可能存在偏差或过时。
任何阅读本项目并用于自身决策的读者，需自行判断、自行承担风险。
作者不对任何因使用本项目代码、数据、或文档导致的财务损失承担责任。
