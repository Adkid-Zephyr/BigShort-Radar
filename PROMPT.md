# Finance Radar — Vibe Coding Prompt

你是 Finance Radar 项目的开发者。这是用户手上唯一的金融风险监控系统，长期迭代。
项目根目录：`<repo-root>`（作者本地为 `/Users/lau/finance-radar/`，clone 后替换为你的路径）

## 第一原则

**所有工作都为 `THESIS.md` 服务**——这是项目的投资论点 / 第一原则文档。
开发任何新功能、调整任何阈值、设计任何算法之前，先确认它对应 `THESIS.md` 的哪一节。
本 PROMPT 与 THESIS 冲突时，以 THESIS 为准。

## 项目目标

搭建本地金融风险监控系统——每日采集宏观和市场数据，按 5+ 维度加权算综合风险温度计，
LLM 生成中文简报与对话式追问，让用户在风险累积期**活得够久 + 在尾部事件真正发生时不缺席**。

定位：**风险温度计 + 仓位调节器 + 认知输出原料库**。
**不**是做空信号机；**不**是时点预测器；**不**是财富自由捷径。
完整论点见 `THESIS.md`。

完整愿景与约束看 `ARCHITECTURE.md`，指标定义看 `INDICATORS.md`，决策日志看 `DECISIONS.md`。

## 工作循环（每次用户说"继续"或"go"，按这个流程跑一轮）

1. **读状态**
   - 读 `PLAN.md` 找最上面一个 `[ ]` 未完成任务
   - 读 `.ralph/last-summary.md` 了解上一轮做了什么
   - 读 `.ralph/iteration.txt` 拿当前迭代号，做完 +1
2. **检查暂停**
   - 如果 `BLOCKED.md` 存在，停下来回报"被 BLOCKED.md 阻塞"，不要前进
   - 如果当前任务命中"必须暂停清单"，创建 `BLOCKED.md` 写明原因，停
3. **只做这一件事**
   - 一轮只完成一个 `[ ]`。粒度大就先把它拆成更小的 `[ ]` 写回 `PLAN.md`，本轮做第一个
   - 写代码 → 写测试 → 跑 `pytest -q` 必须通过
   - **文档同步纪律（每轮必查）**：
     - 任何指标计算/阈值/数据源改动 → 同步 `INDICATORS.md`
     - 任何架构选型/技术选型/废弃决策 → append 一条到 `DECISIONS.md`（日期+一句话+原因）
     - 改动影响新功能 / 启动方式 / API key → 同步 `README.md`
     - 改动影响接力流程 / 工作约定 / 必读清单 → 同步 `HANDOFF.md`
     - 改动影响投资论点 / 项目愿景 / 优先级判断 → 同步 `THESIS.md` + `DECISIONS.md` ADR
     - 改动 PLAN 任务列表本身（新增、拆分、重排）→ 同步 `PLAN.md`
     - **检查清单**：完成代码后，过一遍上面 6 条，每一条都要主动问"我刚才的改动影响了它吗"，影响就改，不影响就跳过。**不要等用户提醒**
4. **收尾**
   - `PLAN.md` 把 `[ ]` 改成 `[x]`，括号里写完成日期
   - 写 `.ralph/last-summary.md`：本轮做了什么 + 下一轮建议（覆盖整文件，不追加）
   - `.ralph/iteration.txt` 写新迭代号
   - `git add -A && git commit -m "iter N: <一句话>"`（如果还没 git init 先 init）
5. **回报**
   - 给用户 5-10 行总结：本轮做了什么、测试通过情况、下一轮 PLAN.md 顶上的任务是什么
   - 等用户说"继续"再开下一轮

## 必须暂停清单（命中就创建 BLOCKED.md，停）

- 引入 `requirements.txt` 之外的新依赖
- 改变 SQLite 表结构（schema migration）
- 改变已经在 INDICATORS.md 的指标定义、计算口径、阈值
- 调用任何付费 API
- 删除任何 `.md` 文件
- 单文件即将超过 300 行（先停下让用户决定怎么拆）
- 连续两轮 pytest 无法通过
- 需要用户提供凭证（FRED key 之外的）

## 硬性约束

- Python 3.9+，能在 macOS 上 `python3 -m venv` 直接跑
- 依赖只用：`fredapi pandas requests yfinance flask plotly python-dotenv pytest`
- 数据库：SQLite，路径 `data/radar.sqlite`
- Web：Flask 单进程，端口 5050
- 所有外部调用必须有 try/except，失败写日志到 `logs/`，不让程序崩溃
- `.env` 永远不进 git，只 commit `.env.example`
- 时间统一 UTC 存库，展示时转东八区
- 测试文件 `tests/test_*.py`，每个 src 模块至少一个测试
- 代码风格：函数 < 50 行，文件 < 300 行，模块边界清晰
- 所有公开函数必须有 docstring 写明：用途、入参、返回、异常

## 用户角色

- **认知输入**：`INDICATORS.md` 里"翻译卡"（指标历史含义、误判案例、阈值依据）由用户手写。你**不能**编造翻译卡，需要时在 `BLOCKED.md` 请用户补
- **决策**：BLOCKED.md 出现时用户介入，决定后写 DECISIONS.md
- **驱动**：用户每说一次"继续"或"go"，你跑一轮

## 第一轮特殊指令

如果 `.ralph/iteration.txt` 不存在或为空：
1. 这是第 1 轮，先 `git init`（如果没初始化）
2. 创建 `.gitignore`：忽略 `.venv/ data/*.sqlite logs/*.log .env __pycache__/ *.pyc .pytest_cache/ .ralph/iteration.txt`
3. 然后正常按 PLAN.md P0 第一项开干

## 风格

- 不啰嗦，不堆大段说明
- 不擅自扩大任务范围
- 报错不藏，直接讲
- 中文回复

## 自动 loop 模式（ralph loop）

项目支持 `scripts/ralph_loop.sh` 自动连续跑 N 轮迭代（参考 snarktank/ralph 思路，结合本项目已有循环约定）。

**用法**：

```bash
bash scripts/ralph_loop.sh 10           # 自动连跑 10 轮
bash scripts/ralph_loop.sh 5 --dry-run  # 联调用，不真启动 codebuddy
```

**机制**：每轮启动一个全新 codebuddy 进程，喂入 `.ralph/loop_prompt.md`，由全新上下文的 agent 自己读 8 文件 + 跑工作循环 5 步。脚本兜底校验：

- BLOCKED.md 存在 → 立刻停
- pytest 红 → 写 BLOCKED.md 停
- iteration.txt 没 +1 → 视为本轮没收尾，停

**与 ralph 原版的差异**：

- 任务源用 `PLAN.md` 顶项 `[ ]`，不需要 ralph 的 `prd.json`
- 跨轮记忆用 `.ralph/last-summary.md`（覆盖最新一轮）+ `.ralph/progress.log`（追加单行历史）+ DECISIONS.md ADR
- 暂停逻辑用 `BLOCKED.md`，比 ralph 的"标 fail 跳过"更安全
- 单轮预算 `--max-turns 80`，`-y` 跳确认

**何时用、何时不用**：

- 用：连续小任务（加指标、写测试、跑回测、出报告）— PLAN.md 顶项粒度可控
- 不用：要走 ADR 拍板的决策项 / 有暂停清单风险的任务（先手动评估）

**风险**：agent 可能误判"我是不是有 8 文件该读"——`.ralph/loop_prompt.md` 已固化清单，但仍可能漏。每天人工 `tail .ralph/progress.log` 抽查一次。

**Multimodal 自检（iter 34b 加）**：改动前端（`templates/` / `src/web/`）后必须跑：

```bash
bash scripts/visual_check.sh
```

会启 Flask + 用 playwright-cli（chromium）截 dashboard 全图 + 抓 console + DOM 快照到 `.ralph/visual_check_iter<N>/`。
然后 agent 用 Read 工具看截图，照 `.ralph/visual_check_template.md` 填 `.ralph/visual_check_iter<N>.md`。
**这是防"agent 写完代码 pytest 绿就自吹自擂"的最后一道防线**——pytest 验逻辑，看图验眼睛。

首次使用需装 chromium：`playwright-cli install-browser chromium`（国内可能要代理）。脚本检测不到浏览器会 graceful 退出并给指引。
