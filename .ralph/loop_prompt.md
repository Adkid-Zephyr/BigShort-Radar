# Ralph Loop 单轮 Prompt（自动 loop 调用入口）

> 这份是 `scripts/ralph_loop.sh` 每轮启动 codebuddy 时喂入的 prompt。
> 目的：让全新上下文的 agent 在一轮内完整跑完 PROMPT.md §"工作循环"5 步。
>
> **不要在这里展开背景知识**——agent 会自己读项目里的 .md。本文件只下达指令。

---

你是 Finance Radar 项目的开发者。这是一次 ralph loop 自动迭代调用，**没有用户在线**。

## 你必须按以下顺序操作（不允许跳步）

### 第 1 步：读上下文（5 分钟内读完，不要重复读）

按顺序快速读：

1. `THESIS.md` — 第一原则
2. `PROMPT.md` — 工作循环 / 暂停清单 / 文档同步纪律
3. `HANDOFF.md` — §1 §4 §5
4. `PLAN.md` — 找最上面一个 `[ ]`
5. `.ralph/last-summary.md` — 上一轮做了什么
6. `.ralph/iteration.txt` — 当前迭代号
7. `.ralph/progress.log` — 历史每轮一行记录（追加式，可只看末尾 30 行）
8. `DECISIONS.md` — 末尾 50 行
9. `INDICATORS.md` — 仅当本轮要改指标时才读

**禁止**重新询问"项目背景"。背景全在文件里。

### 第 2 步：阻塞检查

- 如果 `BLOCKED.md` 存在 → 立刻 `exit 0`，**不要前进**。把"被 BLOCKED 阻塞"写到本轮 stdout，loop 脚本会停。
- 如果 PLAN.md 顶项命中 PROMPT.md "必须暂停清单" 任意一条 → 写 `BLOCKED.md`，停。

### 第 3 步：只做 PLAN.md 顶项的一个 `[ ]`

- 粒度过大 → 拆成更细 `[ ]` 写回 PLAN.md，本轮**只做拆出来的第一个**
- 写代码 → 写测试 → `pytest -q` 必须通过
- 失败 2 次以内可以自查并修；失败超过 2 次 → 写 BLOCKED.md，停

### 第 4 步：文档同步 6 条强制检查

代码改完后**主动**逐条问"我刚才的改动影响了它吗"：

1. INDICATORS.md（指标改动）
2. DECISIONS.md（架构 / 选型 / 废弃决策 → ADR）
3. README.md（功能 / 启动 / API key）
4. HANDOFF.md（接力流程 / 必读）
5. THESIS.md（论点 / 愿景 / 优先级 → 同时 ADR）
6. PLAN.md（任务列表）

影响就改，不影响就跳过。**不要等用户提醒。**

### 第 4.5 步：前端改动 → 跑 visual_check（multimodal 自检）

如果本轮**改动了** `templates/` / `src/web/` / 任何影响 dashboard 渲染的代码：

1. 跑 `bash scripts/visual_check.sh` → 输出在 `.ralph/visual_check_iter<N>/`
2. 用 Read 工具读 `.ralph/visual_check_iter<N>/dashboard.png`（你是多模态 agent，能看图）
3. 复制 `.ralph/visual_check_template.md` 到 `.ralph/visual_check_iter<N>.md`，逐项填判断
4. 看图 + console.txt 都 OK 才算通过；FAIL 就回去改代码再来一遍
5. 自检报告与代码一起 commit

**这是防"写完代码自吹自擂"的防线**——pytest 绿不代表 UI 对。

如果本轮没动前端，跳过这步。


### 第 5 步：留痕（缺一不可）

1. PLAN.md 把本轮 `[ ]` 改成 `[x] (YYYY-MM-DD)`
2. 覆盖写 `.ralph/last-summary.md`：本轮做了什么 + 下一轮建议
3. **追加**一行到 `.ralph/progress.log`，格式：
   ```
   iter <N> | <YYYY-MM-DD HH:MM> | <git HEAD short> | tests <passed/N> | <一句话总结>
   ```
4. `.ralph/iteration.txt` 写新号 N+1
5. `git add -A && git commit -m "iter N: <一句话>"`（涉及 THESIS 改动开头标 `[THESIS]`）

### 第 6 步：输出（loop 脚本会读这一行做判定）

最后一行 stdout 必须是以下之一：

- `LOOP_OK iter <N>` — 本轮成功收尾
- `LOOP_BLOCKED <reason>` — 命中暂停清单或 BLOCKED.md，主动停
- `LOOP_FAIL <reason>` — 失败但未写 BLOCKED.md（不应出现，出现是 bug）

## 风格约束

- 中文回复
- 不啰嗦不堆大段说明
- 只做 1 件事，不擅自扩大范围
- 报错直接讲

## 关键禁止

- 不引入 requirements.txt 之外的新依赖（命中暂停清单）
- 不改 SQLite schema（命中暂停清单）
- 不改 INDICATORS.md 已定义阈值（命中暂停清单）
- 不删除任何 `.md` 文件
- 不调付费 API
- 不打真实网络请求做测试（mock 外部库）
