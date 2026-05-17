# Visual Check Report — iter 35

## 1. 改动摘要

- 改了什么文件：
  - `src/web/source_links.py`（新建）— FRED:/YF:/OECD:/CBOE: 前缀映射官方 URL
  - `src/web/app.py` — 注册表加 `source_url`，`_build_rows` 注入
  - `templates/index.html` — source 列改成 `<a class="source-link">`，加 hover/箭头 CSS
- 期望 UI 看到的变化：
  - 每条指标的"来源"列从纯文本变成可点击蓝色链接，hover 有底色变化、链接末尾 ↗ 箭头
  - 点击新页签打开（target=_blank + rel noopener）
  - 链接到正确的官方页：FRED 系列 → fred.stlouisfed.org/series/<id>，^VIX → finance.yahoo.com/quote/%5EVIX
  - 派生/无数据行不变（值列保持 empty 占位）
- 不期望出现的回归：
  - 表格排版乱（新增 anchor 元素的高度变化）
  - 主题色冲突（链接蓝色 #60a5fa 应该和深色主题搭）

## 2. 自检命令

```bash
bash scripts/visual_check.sh --no-flask
```

**结果**：chromium 浏览器未安装（`~/Library/Caches/ms-playwright` 里没 chromium 子目录），脚本 graceful 退出 rc=1。

替代验证：直接 `curl` 渲染后的 HTML，人工 grep + 用户浏览器肉眼看。

## 3. 看图判断

### 3.1 必查项（替代验证：curl HTML grep + tests/test_web.py 端到端）

- [x] 页面正常渲染 — `curl http://127.0.0.1:5050/` HTTP 200，20054 字节
- [x] 综合温度计 gauge 在（HTML 里有 `gauge-title`、`risk.date`）
- [x] 5 个分组（波动率/曲线/信用/流动性/跨市场）都在
- [x] 每条指标显示：名 + 当前值 + 颜色 + 更新时间 + 来源
- [x] LLM 简报段（briefing）渲染（HTML 含 `briefing` class）
- [x] chatbot 浮窗按钮可见（HTML 含 chat 浮窗 div）

### 3.2 本轮新增专项

- [x] source 列每个有数据的行渲染为 `<a class="source-link">`（grep HTML：9 条匹配）
- [x] FRED:T10Y2Y → https://fred.stlouisfed.org/series/T10Y2Y ✅
- [x] FRED:BAMLH0A0HYM2 → https://fred.stlouisfed.org/series/BAMLH0A0HYM2 ✅
- [x] YF:^VIX → https://finance.yahoo.com/quote/%5EVIX（^ 正确 url-encode） ✅
- [x] FRED:SOFR-IORB（派生）→ registry 手填回 https://fred.stlouisfed.org/series/SOFR ✅
- [x] target="_blank" + rel="noopener noreferrer" 都在
- [x] CSS：.source-link 蓝色 #60a5fa + hover 变深 + ::after ↗ 箭头

### 3.3 回归检查

- [x] `pytest -q` 197 通过 / 0 失败（+18 新测试）
- [x] 现有 `test_index_renders_with_data` 仍通过（未破坏）
- [x] 老的 `YF:^VIX` 文本断言仍然命中（label 内容没动）
- [ ] **未做**：浏览器肉眼看截图（chromium 没装）。需用户在浏览器手工开 http://127.0.0.1:5050/ 看

## 4. 看图发现的问题

- **未数据的行（vix_term_structure 那条）**：colspan=4 把整个剩余区占了"暂无数据"提示，导致 source URL 即使在 registry 里手填了也看不见。后续应改：empty 行也保留 source 列展示链接（让用户知道"这条数据该去哪官方页查"）。**写回 PLAN.md 作为下一轮小改进。**

- chromium 浏览器装不上（疑似下载源被墙/超时）→ visual_check.sh 自动截图链路在本机暂时不可用。已 graceful 降级，不阻塞主线。建议下一轮 multimodal 自检改用 ComputerUse 截系统屏幕的 fallback 路径。

## 5. 结论

- [x] **PASS** — 主体功能符合预期，9 条有数据的指标全部正确渲染外链。pytest 与 HTML grep 双重验证通过。
- 未数据行的 source 链接展示是已知边角，不阻塞合并，下一轮修。

## 6. TODO（如果 FAIL）

- [ ] 模板 empty 行也保留 source 链接列（PLAN.md P3.6 加一项）
- [ ] chromium 装好后回头跑一次真实 visual_check 验证 CSS hover/箭头
