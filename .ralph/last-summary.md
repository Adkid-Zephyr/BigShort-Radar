# 上一轮总结

迭代 36（2026-05-17）：合并两件事——empty 行 source 链接修复 + GitHub 公开化推送。

本轮做了：

## A. empty 行 source 链接（小改进，前端）

- `templates/index.html`：empty 行 `colspan=4` → `colspan=3`，新加独立 source 列展示"查源"链接（registry 手填 url 时可见）
- `tests/test_web.py`：加回归断言（empty 路径含 cboe.com 与"查源"）
- `.ralph/visual_check_iter36.md`：自检报告（chromium 装不上走 curl-grep + pytest 双重验证）

## B. GitHub 公开化（大动作，史诗级 git surgery）

按用户拍板的 4 项决策：
- public 仓库 `Adkid-Zephyr/BigShort-Radar`
- CC BY-NC 4.0
- THESIS 双份处理（私有原稿不进 git）
- README 全量重写

具体做了：
1. 新建 `THESIS_PUBLIC.md` 脱敏版：删个人桌面路径、§5.3 仓位映射保留方法论但去金额、加 §9 免责声明
2. `.gitignore` 加 `THESIS.md` + `git rm --cached THESIS.md`
3. **`git filter-branch --index-filter` 重写整段 git 历史**扫净 THESIS.md（推送前完整目录备份到 `~/finance-radar.backup-20260517_172848`）
4. `LICENSE` CC BY-NC 4.0 + 项目特定免责段
5. **`README.md` 全量重写**（240+ 行）：targets 接力开发者 + 公开访客双视角，含当前进度快照 / 架构图 / 10 指标阈值表 / 综合温度计算法 / LLM 集成 / launchd / Ralph Loop / Multimodal 自检 / 一分钟启动 / API key / 文件导览 / 路线图
6. 路径相对化：PROMPT/HANDOFF 里 `/Users/lau/finance-radar/` → `<repo-root>`
7. GitHub repo 创建走 API（POST /user/repos）
8. Push 用 `git -c http.extraHeader="Authorization: Basic $(base64 user:token)"`，**token 不进任何 remote URL / config 文件 / 日志**
9. 验证 GitHub 上没有 THESIS.md / .env / data/ / .ralph/iteration.txt / loop_runs.log

测试：pytest 197 通过 / 0 失败 / 0 skip（前端改动 1 个新断言）。

git：
- iter 35 1123cd5 → iter 36 公开化前 d4eea0f → 公开化后 3be0d95（filter-branch 后所有 hash 都变了）
- 推送到 GitHub：<https://github.com/Adkid-Zephyr/BigShort-Radar>

文档同步：PLAN.md（[x] empty 行 + [x] GitHub 推送）/ DECISIONS.md（iter 36 ADR）/ HANDOFF.md / PROMPT.md（路径相对化）。

## 已知遗留

- chromium 浏览器仍未装（10+ 分钟卡住，疑似下载源被墙）→ visual_check.sh graceful 退出，等用户网络条件好时一句 `playwright-cli install-browser chromium` 修
- token 在对话里出现过 = 已暴露，但用户拍板 push 后不吊销。本地 git remote URL 干净，无 token 残留

## 下一项 PLAN

按 THESIS §6 优先级：

- **iter 37：历史回测框架**（最高优先，THESIS §6.1）
  - 新建 `src/backtest/loader.py` 拉 FRED 历史长序列到独立缓存库 `data/backtest_cache.sqlite`
  - `src/backtest/runner.py` 反向跑温度计
  - 不动主流程、不改主 schema、不改 INDICATORS 阈值
  - 这是项目从"凭印象拍阈值"转"用历史校准阈值"的转折点

候选下一步备选：
- iter 38：z-score / 历史分位替换三档跳变
- iter 39：加速度分量（过去 N 天斜率）
- iter 40：维度间乘法叠加 + 组合信号检测
- iter 41：融资市场维度补缺（FRA-OIS / USD basis swap / 国债基差杠杆）

下一句"继续"将进 iter 37 历史回测。
