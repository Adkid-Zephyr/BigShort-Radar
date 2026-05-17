# 上一轮总结

迭代 34b（2026-05-17）：ralph loop multimodal 自检层落地。

本轮做了：

- 新建 `scripts/visual_check.sh`（可执行）：
  - 自起 Flask:5050（除非 `--no-flask`），用 `playwright-cli`（chromium）截 1440×900 dashboard 全图 + DOM 快照 + console + flask log
  - 输出到 `.ralph/visual_check_iter<N>/`
  - graceful 降级：检测不到 chromium 自动 rc=1 + 清晰指引（不会卡死）
  - trap EXIT 自动 cleanup（停 Flask + 关 playwright session）
- 新建 `.ralph/visual_check_template.md`：6 section 报告模板（改动摘要 / 自检命令 / 看图判断必查项 / 看图问题 / 结论 PASS-FAIL-PARTIAL / TODO）
- 更新 `.ralph/loop_prompt.md` §4.5：改动 `templates/` 或 `src/web/` 必须跑 visual_check + 用 Read 看图 + 写报告。明确这是"防 pytest 绿但 UI 烂"的最后一道线
- 新建 `tests/test_visual_check.py`：7 用例验脚本骨架（不真启浏览器），mock 的方式是直接 grep 脚本内容
- 文档同步：PROMPT.md §自动 loop 模式补 multimodal 自检段 / HANDOFF.md §10 / PLAN.md P3.6 标 [x] / DECISIONS.md iter 34b ADR / .gitignore 加 visual_check_iter*/ + .playwright-cli/

测试：pytest 179 通过 / 0 失败 / 0 skip（+12 个新测试）。

git：iter 34a 6918d4e → iter 34b 待 commit。

**遗留事项（不阻塞）**：本机 chromium 安装在 `playwright-cli install-browser chromium` 步骤卡了 10+ 分钟未完成（疑似下载源/网络问题），脚本已加 graceful 降级。等用户网络条件好时一键装：

```bash
playwright-cli install-browser chromium
# 国内可能需 HTTPS_PROXY 或 PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
```

下一项 PLAN（按 THESIS §6 优先级）：

- **iter 35：历史回测框架**（最高优先，THESIS §6.1）
  - 新建 `src/backtest/loader.py`：从 FRED 拉 8 条已上线指标的历史长序列（2006-01 至今），缓存到独立 `data/backtest_cache.sqlite`
  - 新建 `src/backtest/runner.py`：给定日期窗口 + 指标集，对历史每天调 thresholds.classify + risk_score，返回 DataFrame
  - 不动主流程、不改主 schema、不改 INDICATORS 阈值
  - 测试：mock FRED，验关键路径
  - 这是项目从"凭印象拍阈值"转"用历史校准阈值"的转折点

候选下一步备选：
- iter 36：z-score / 历史分位替换三档跳变（THESIS §6.2）
- iter 37：加速度分量（过去 N 天斜率）
- iter 38：维度间乘法叠加 + 组合信号检测
- iter 39：融资市场维度补缺（FRA-OIS / USD basis swap / 国债基差杠杆）

按用户授权"先做工程基础设施，再开科学校准"，工程基础设施已就绪。下一句"继续"将进 iter 35（真正的科学校准开始）。
