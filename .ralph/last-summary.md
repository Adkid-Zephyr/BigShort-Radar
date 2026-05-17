# 上一轮总结

迭代 35（2026-05-17）：指标 source 列改成可点击官方页外链。

本轮做了：

- 新建 `src/web/source_links.py`：纯函数 `source_url(source) -> str | None`，按前缀分发
  - `FRED:T10Y2Y` → `https://fred.stlouisfed.org/series/T10Y2Y`
  - `YF:^VIX` → `https://finance.yahoo.com/quote/%5EVIX`（^ 正确 url-encode）
  - `OECD:` → 搜索页（OECD 没稳定直链）
  - `CBOE:` → `cboe.com/tradable_products/<lower>/`
  - 未知前缀 / 多源派生 / 空 ident → None（由 registry 手填兜底）
- `src/web/app.py` 注册表加 `source_url` 字段：
  - VIX 期限结构（派生）→ CBOE VIX options 规格页
  - SOFR-IORB（派生 source 串带 `-`）→ FRED SOFR 主页
  - 其他 8 条全靠 source_links 自动推导
- `templates/index.html`：source 列改成 `<a class="source-link" target="_blank" rel="noopener noreferrer">`，蓝色 #60a5fa + hover 变深 + 末尾 ↗ 箭头
- 测试：`test_source_links.py` 14 用例（FRED/Yahoo/OECD/CBOE/边界）+ `test_web.py` 加 1 个 e2e 断言
- 自检：visual_check.sh chromium 没装走 graceful 退出，改用 curl + grep + pytest 三重验证。9 条有数据指标全部正确渲染外链。报告 `.ralph/visual_check_iter35.md`
- 文档同步：PLAN.md（[x] + 新增 empty 行修复 [ ]）/ DECISIONS.md（iter 35 ADR）

测试：pytest 197 通过 / 0 失败 / 0 skip（+18 新测试）。

git：iter 34b 5ed4fff → iter 35 待 commit。

**已知边角（下一轮可顺手修）**：
- VIX 期限结构那条因当前 DB 无数据，模板 `colspan=4` 占位"暂无数据"把 source 列吞了，链接不可见。即便没数据，让 source 链接也露出更友好。已写入 PLAN.md P3.6 工程化基础设施段。

下一项 PLAN（按 THESIS §6 优先级）：

- **iter 36：empty 行也保留 source 链接**（小改进，10 分钟）
- **iter 37：历史回测框架**（THESIS §6.1，最高优先）
  - 新建 `src/backtest/loader.py` 拉 FRED 历史长序列到独立缓存库
  - `src/backtest/runner.py` 反向跑温度计
  - 不动主流程

或用户优先：
- 装 chromium 让 visual_check 真正能跑：`playwright-cli install-browser chromium`（国内代理）

下一句"继续"将进 iter 36（小改进）或 iter 37（历史回测，按 THESIS 优先级）。
