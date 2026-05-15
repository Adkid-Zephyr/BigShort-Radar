# HANDOFF — Finance Radar 开发接力手册

> 这份是给任何接手开发的 agent / 新会话看的。读完这一页就能无缝继续。
> 维护原则：每次开发动作前先看 §1，做完后按 §6 留痕。

---

## 1. 30 秒上下文

- **项目**：Finance Radar，本地金融风险监控 MVP，唯一作者：用户 lau
- **根目录**：`/Users/lau/finance-radar/`
- **工作宪法**：`PROMPT.md`（必读，规定每轮做什么、暂停清单、硬性约束）
- **当前主线**：P0 已收官（VIX 上线 + Flask 渲染绿灯），正在做 P1 的 FRED 系列指标
- **唯一驱动指令**：用户说"继续"或"go"→ 跑下一轮迭代

## 2. 必读文件清单（按顺序）

| 顺序 | 文件 | 看什么 |
|---|---|---|
| 1 | `PROMPT.md` | 工作循环 5 步、必须暂停清单、硬性约束 |
| 2 | `PLAN.md` | 找最上面一个 `[ ]` 未完成项，那就是本轮任务 |
| 3 | `.ralph/last-summary.md` | 上一轮做了什么、留下什么、建议下一轮做什么 |
| 4 | `.ralph/iteration.txt` | 当前迭代号（做完 +1） |
| 5 | `DECISIONS.md` | 项目历史选型与原则；关键如"重复三次再抽象"、阈值边界规则 |
| 6 | `INDICATORS.md` | 指标定义、阈值、翻译卡（翻译卡只能用户手写，模型不能编造） |
| 7 | `ARCHITECTURE.md` | 模块边界与数据流（fetch/store/compute/web/utils） |

如果存在 `BLOCKED.md` → **立即停下**，回报"被 BLOCKED.md 阻塞"，不要前进。

## 3. 跑环境

- venv：`/Users/lau/finance-radar/.venv/bin/python`
- 跑测试：`cd /Users/lau/finance-radar && .venv/bin/python -m pytest -q`
- 跑 daily fetch：`.venv/bin/python -m scripts.daily_fetch`
- 起 Flask：`.venv/bin/python -m src.web.app`，浏览器打开 http://localhost:5050
- 已装依赖（白名单内）：Flask、fredapi、pandas、pytest、python-dotenv、requests、yfinance
- 还没装的白名单依赖：plotly（用到再 pip）

## 4. 关键约定（高频踩坑点）

- **暂停清单 8 条**（PROMPT.md §"必须暂停清单"）：碰到任何一条 → 写 `BLOCKED.md` 停。最常见的是"引入白名单外依赖"。
- **每轮一件事**：PLAN.md 顶上一个 `[ ]`。粒度过大就先拆 `[ ]` 写回 PLAN.md，本轮只做拆出来的第一个。
- **重复三次再抽象**（DECISIONS.md 2026-05-15 条）：vix.py 那个"遍历 series + 写库"循环，到第三个 FRED 指标时再抽 store helper，不要预判抽象。
- **阈值边界规则**（DECISIONS.md）：
  - up 方向：`v == low` → GREEN；`v == high` → YELLOW；`v > high` 才 RED
  - down 方向：`v == high` → GREEN；`v == low` → YELLOW；`v < low` 才 RED
- **时间约定**：UTC 入库，展示转东八区
- **时间戳**：`ingested_at` 用 `_utc_now_iso()`（db.py 里有），不要自己拼
- **失败处理**：所有外部调用 try/except，写日志，返回 None 或 0，不要让程序崩
- **测试**：每个 src 模块至少一个测试；mock 外部库，不打真实网络
- **翻译卡**：INDICATORS.md 里"翻译卡"段只能用户手写。模型只填到"待用户补"

## 5. 现状基线（截至 2026-05-15）

- 18 个 commit 全在 main，工作树 clean
- pytest 65 通过 / 0 失败 / 0 skip
- 已实现指标：VIX（yfinance: ^VIX）342 条真实数据已入库
- FRED key 已写 `.env`（已 .gitignore），fred_client.py 真打网络验证 T10Y2Y=0.48 成功
- 下一项 PLAN 顶上的 `[ ]`：`src/compute/indicators/yield_curve.py`：10Y-2Y（FRED: T10Y2Y）
- yield_curve_10y2y 阈值（INDICATORS.md 已写好）：GREEN >0.5 / YELLOW 0–0.5 / RED <0，方向 down

## 6. 留痕规范（每轮收尾必做）

每轮完成后按这个顺序留痕，缺一不可：

1. **代码**：写代码 + 写测试 + `pytest -q` 必须全过
2. **PLAN.md**：把本轮的 `[ ]` 改成 `[x] (YYYY-MM-DD)`
3. **INDICATORS.md / DECISIONS.md**：有指标改动 / 选型改动就同步 append
4. **`.ralph/last-summary.md`**：覆盖写本轮做了什么 + 下一轮建议（不追加，覆盖）
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

不要重新开会问用户"项目背景是什么"。读 §2 的 7 个文件，5 分钟你就掌握全貌。
不要重写已有模块；不要为了"更优雅"擅自重构（重构是单独一轮迭代）。
不要编造翻译卡。不要在没用户拍板时做决策项。
报错直接讲。中文回复。
