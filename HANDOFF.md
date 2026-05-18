# HANDOFF — Finance Radar 开发接力手册

> 这份是给任何接手开发的 agent / 新会话看的。读完这一页就能无缝继续。
> 维护原则：每次开发动作前先看 §1，做完后按 §6 留痕。

---

## 1. 30 秒上下文

- **项目**：Finance Radar，本地金融风险监控系统，唯一作者：用户 lau
- **根目录**：`<repo-root>`（作者本地 `/Users/lau/finance-radar/`，clone 后替换）
- **第一原则**：`THESIS.md`（**必读**，项目投资论点 / 危机传导链 / 反共识结构性观察）
- **工作宪法**：`PROMPT.md`（必读，工作循环 / 暂停清单 / 硬性约束 / 文档同步纪律）
- **当前主线**：MVP 已收官（10 指标 / 5 维度 / 综合温度计 / LLM 简报 / chatbot / launchd），下一阶段重点是历史回测校准 + 算法升级（z-score / 加速度 / 组合信号）+ 融资市场维度补缺
- **唯一驱动指令**：用户说"继续"或"go"→ 跑下一轮迭代

## 2. 必读文件清单（按顺序）

| 顺序 | 文件 | 看什么 |
|---|---|---|
| 1 | `THESIS.md` | **第一原则**——投资论点、危机传导链、反共识观察。所有工作为它服务 |
| 2 | `PROMPT.md` | 工作循环 5 步、必须暂停清单、硬性约束、**文档同步纪律** |
| 3 | `PLAN.md` | 找最上面一个 `[ ]` 未完成项，那就是本轮任务 |
| 4 | `.ralph/last-summary.md` | 上一轮做了什么、留下什么、建议下一轮做什么 |
| 5 | `.ralph/iteration.txt` | 当前迭代号（做完 +1） |
| 6 | `DECISIONS.md` | 项目历史选型与原则；ADR 风格 |
| 7 | `INDICATORS.md` | 指标定义、阈值、翻译卡（翻译卡只能用户手写，模型不能编造） |
| 8 | `ARCHITECTURE.md` | 模块边界与数据流（fetch/store/compute/web/utils） |

如果存在 `BLOCKED.md` → **立即停下**，回报"被 BLOCKED.md 阻塞"，不要前进。

## 3. 跑环境

- venv：`<repo-root>/.venv/bin/python`
- 跑测试：`cd <repo-root> && .venv/bin/python -m pytest -q`
- 跑 daily fetch：`.venv/bin/python -m scripts.daily_fetch`
- 起 Flask：`.venv/bin/python -m src.web.app`，浏览器打开 http://localhost:5050
- 已装依赖（白名单内）：Flask、fredapi、pandas、pytest、python-dotenv、requests、yfinance
- 还没装的白名单依赖：plotly（用到再 pip）
- LLM：阿里百炼 Coding Plan（`qwen3-coder-plus`），key 在 `.env`，不进 git

## 4. 关键约定（高频踩坑点）

- **THESIS 优先**：所有改动先回头确认对应论点章节。THESIS 与 PROMPT/PLAN 冲突时以 THESIS 为准
- **文档同步纪律**：每轮代码改完后，主动过一遍 PROMPT §3 的 6 条检查清单——不要等用户提醒
- **暂停清单 8 条**（PROMPT.md §"必须暂停清单"）：碰到任何一条 → 写 `BLOCKED.md` 停。最常见的是"引入白名单外依赖"
- **每轮一件事**：PLAN.md 顶上一个 `[ ]`。粒度过大就先拆 `[ ]` 写回 PLAN.md，本轮只做拆出来的第一个
- **重复三次再抽象**（DECISIONS.md 2026-05-15 条）：避免预判抽象，等真实重复出现 3 次再抽 helper
- **阈值边界规则**（DECISIONS.md）：
  - up 方向：`v == low` → GREEN；`v == high` → YELLOW；`v > high` 才 RED
  - down 方向：`v == high` → GREEN；`v == low` → YELLOW；`v < low` 才 RED
- **时间约定**：UTC 入库，展示转东八区
- **失败处理**：所有外部调用 try/except，写日志，返回 None 或 0，不要让程序崩
- **测试**：每个 src 模块至少一个测试；mock 外部库，不打真实网络
- **翻译卡**：INDICATORS.md 里"翻译卡"段只能用户手写。模型只填到"待用户补"
- **LLM 失败优雅降级**：daily_fetch 主流程不依赖 LLM，LLM 不可用时简报跳过，指标照常入库

## 5. 现状基线（截至 2026-05-17 iter 33）

- 34 commits（含 iter 33 THESIS 落地），main 分支唯一，工作树 clean
- pytest 167 通过 / 0 失败 / 0 skip
- 已实现指标（10 条 / 5 维度）：
  - 波动率：VIX、VIX 期限结构（VIX/VIX3M）
  - 曲线：10Y-2Y、10Y-3M
  - 信用：HY OAS、IG OAS
  - 流动性：SOFR-IORB
  - 跨市场：USDJPY、DXY 广义、日本 10Y
- 综合温度计：五维加权（曲线 25 / 信用 25 / 跨市场 20 / 流动性 15 / 波动率 15）→ 0-100 分 / 三档
- LLM：百炼 qwen3-coder-plus，每日简报 + dashboard chatbot 浮窗

> **iter 56 实时基线（2026-05-17）**：pytest 492/0/0；19 条指标 / 7 维度（含中国 + 政策）；7 个 Web page 全活；前端 iter 55-56 两轮美化(信息驾驶舱方向 SVG 圆环 cockpit gauge + Bento 5 列 + 校准 stacked bar)。
>
> **iter 57 实时基线（2026-05-17）**：pytest 504/0/0;阈值校准三件套完成 — 派生指标回测现场计算(`src/backtest/derived.py`),维度内 max 触顶,切点 65→60。三窗口重跑 2008/COVID/2022 RED 天数 33/42/393。SUMMARY.md 重新生成。
>
> **iter 58 实时基线（2026-05-18）**：pytest 505/0/0;VIX 主流程从 yahoo `^VIX` 切 FRED `VIXCLS`,修复 dashboard 核心波动率指标受 yahoo 限速导致"积累中"的问题。真实 FRED 写入主 DB 10 条,latest 2026-05-14 17.26。
>
> **iter 59 实时基线（2026-05-18）**：pytest 506/0/0;VIX 期限结构从 yahoo `^VIX/^VIX3M` 切 FRED `VIXCLS/VXVCLS`,主 DB 回填 VIX 1629 条 / 期限结构 1600 条,latest ratio=0.8278。
>
> **iter 60 实时基线（2026-05-18）**：pytest 520/0/0;新增 CBOE 官方源三条期权交易者指标:VIX9D 短端恐慌 / VIX1Y 长端恐慌 / Total Put-Call Ratio。真实写入主 DB:VIX9D 11 条 latest 16.37,VIX1Y 11 条 latest 24.04,Put/Call 当日 0.93。当前总指标 22 条 / 7 维度。
>
> **iter 61 实时基线（2026-05-18）**：pytest 520/0/0;VVIX/SKEW 从 yahoo `^VVIX/^SKEW` 切 CBOE 官方 CSV,真实写入主 DB VVIX 11 条 latest 92.94 / SKEW 11 条 latest 145.77。dashboard 波动率核心空白基本补齐。
>
> **iter 62 实时基线（2026-05-18）**：pytest 522/0/0;新增第 8 维“期权情绪”,Put/Call 从波动率拆出并拆 total/index/equity 三条。权重:曲线18/信用18/流动性13/波动率10/期权情绪8/跨市场13/政策10/中国10。真实写入主 DB total=0.93,index=1.03,equity=0.59。
- launchd：每天北京 05:30 自动跑（已加载 `~/Library/LaunchAgents/com.financeradar.daily.plist`）
- 当前下一项 PLAN：按 `THESIS.md` §6 列出的优先级走（历史回测 → 算法升级 → 融资市场维度补缺 → 政策反应维度新增）

## 6. 留痕规范（每轮收尾必做）

每轮完成后按这个顺序留痕，缺一不可：

1. **代码**：写代码 + 写测试 + `pytest -q` 必须全过
2. **文档同步检查**（按 PROMPT §3 的 6 条逐条过）：
   - INDICATORS.md（指标改动）
   - DECISIONS.md（架构/选型/废弃决策）
   - README.md（功能/启动/API key）
   - HANDOFF.md（接力流程/必读）
   - THESIS.md（论点/愿景/优先级 → 同时 ADR）
   - PLAN.md（任务列表）
3. **PLAN.md**：把本轮的 `[ ]` 改成 `[x] (YYYY-MM-DD)`
4. **`.ralph/last-summary.md`**：覆盖写本轮做了什么 + 下一轮建议
5. **`.ralph/iteration.txt`**：写新迭代号
6. **git**：`git add -A && git commit -m "iter N: <一句话>"`
7. **回报用户**：5–10 行总结，包括本轮做了什么、测试通过情况、下一轮顶上是什么
8. **WorkBuddy memory**（可选但推荐）：当前会话工作区下 `.workbuddy/memory/YYYY-MM-DD.md` 追加一段，方便跨会话回看

## 7. 暂停清单（再贴一遍，最容易踩）

碰到这些**必须**停下写 BLOCKED.md：

- 要装 requirements.txt 之外的新依赖
- 要改 SQLite 表结构
- 要改 INDICATORS.md 已定义的指标口径或阈值
- 要调用付费 API
- 要删除任何 `.md` 文件
- 单文件即将 >300 行
- 连续两轮 pytest 没过
- 需要 FRED key 之外的用户凭证

## 8. 给下一个接手的 agent 的话

不要重新开会问用户"项目背景是什么"。读 §2 的 8 个文件（**THESIS 第一**），5 分钟你就掌握全貌。
不要重写已有模块；不要为了"更优雅"擅自重构（重构是单独一轮迭代）。
不要编造翻译卡。不要在没用户拍板时做决策项。
**不要等用户提醒文档同步——这是基本职业素养，不是额外工作**。
报错直接讲。中文回复。

## 9. 自动 loop 模式（ralph loop）

iter 34 起项目支持 `scripts/ralph_loop.sh` 自动连续跑 N 轮：

```bash
bash scripts/ralph_loop.sh 10
```

每轮启动全新 codebuddy 进程，喂入 `.ralph/loop_prompt.md`。脚本兜底校验：
- BLOCKED.md 存在 → 停
- pytest 红 → 写 BLOCKED 停
- iteration.txt 没 +1 → 停

完整说明见 `PROMPT.md` §"自动 loop 模式"。
跨轮单行进度记录在 `.ralph/progress.log`（追加式，不要覆盖写）。

## 10. Multimodal 自检（iter 34b）

改动前端（`templates/` / `src/web/`）后必须：

```bash
bash scripts/visual_check.sh
```

输出到 `.ralph/visual_check_iter<N>/`：dashboard.png / dom.yaml / console.txt / flask.log。
然后用 Read 工具看截图，照 `.ralph/visual_check_template.md` 填 `.ralph/visual_check_iter<N>.md`。

**首次需装浏览器**：`playwright-cli install-browser chromium`（国内可能要代理或 npm mirror）。

防"pytest 绿但 UI 烂"的最后一道线。
