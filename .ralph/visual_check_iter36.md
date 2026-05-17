# Visual Check Report — iter 36

## 1. 改动摘要

- 改了什么文件：
  - `templates/index.html` empty 行从 `colspan=4` 改 `colspan=3`，新增独立 source 列，registry 手填 url 时显示"查源"链接
  - `tests/test_web.py` 加 1 个回归断言（empty 行也含 cboe.com 与"查源"）
  - 后续：`THESIS_PUBLIC.md` / `LICENSE` / `README.md`（与前端无关）

- 期望 UI 看到的变化：
  - VIX 期限结构那行（当前 DB 无值）原来是"暂无数据"占整行 4 列，现在变成"暂无数据"占 3 列 + 独立 source 列展示"查源"链接 → CBOE VIX options 规格页

## 2. 自检命令

```bash
bash scripts/visual_check.sh --no-flask
```

**结果**：chromium 浏览器仍未装（前一轮装了 10+ 分钟卡住，被墙）→ graceful 退出 rc=1。

替代验证：curl HTML + grep + pytest e2e。

## 3. 看图判断（替代验证）

### 3.1 必查项

- [x] HTTP 200，HTML 完整渲染（curl 拿到完整内容）
- [x] empty 行的 source 列出现 `<a class="source-link" href="https://www.cboe.com/...">查源</a>`
- [x] 9 条有数据指标的 source 链接照常工作
- [x] pytest 197/197 通过（含本轮新加的 empty-row 回归断言）

### 3.2 本轮新增专项

- [x] VIX 期限结构行点击"查源" → CBOE VIX options 规格页
- [x] empty 行 colspan=3 不再吞掉 source 列（grep 模板可见 `colspan="3"`）
- [x] registry 没填 source_url 的 empty 行展示 `—`（占位符）

### 3.3 回归检查

- [x] iter 35 加的 9 条 source 链接都还在
- [x] target="_blank" + rel="noopener noreferrer" 仍正确

## 4. 看图发现的问题

- chromium 装不了导致没有截图，靠 curl + grep 替代。等用户网络条件好时一句 `playwright-cli install-browser chromium` 就能完整跑。

## 5. 结论

- [x] **PASS** — 主体功能符合预期。pytest + HTML grep 双重验证通过。
- 后续浏览器装好后回头跑一次完整 visual_check 确认 CSS hover/箭头样式。

## 6. TODO（如果 FAIL）

无。
