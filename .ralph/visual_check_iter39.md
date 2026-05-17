# Visual Check Report — iter 39

## 1. 改动摘要

- 改了什么文件：
  - `src/web/sparkline.py`（新建，165 行）：纯函数 `build_sparkline_svg(values, threshold_low, threshold_high, direction)` 出 inline SVG 折线 + 三档阈值带 + 末点高亮
  - `src/web/app.py`：registry 加 thresholds 元信息（引用模块常量）；`_build_rows` 注入 sparkline_svg；`_fetch_sparkline_values` 优先 cache DB，主 DB 兜底
  - `templates/index.html`：表头加"90 天"列，行里渲染 `r.sparkline_svg | safe`，加 `.spark-cell` CSS（vertical-align middle / 132px 宽）
- 期望 UI 看到的变化：
  - 每条指标行新增"90 天"列，显示一条 120×28px 微折线
  - 已回填 5 年历史的 8 条指标显示真实折线 + 三档颜色阈值带 + 蓝色末点高亮
  - 派生指标（VIX 期限结构 / SOFR-IORB）+ Yahoo 限速漏拉的 VIX，显示"积累中 (n/10)"占位

## 2. 自检命令

```bash
bash scripts/visual_check.sh
# chromium 仍未装 → graceful 退出 rc=1
```

替代：curl HTML + grep + pytest 三重验证。

## 3. 看图判断（curl 替代）

### 3.1 必查项

- [x] HTTP 200，HTML 32251 字节（比 iter 38 后的 20054 字节多 12KB，都是 SVG 数据）
- [x] 10 个 `<svg>` 标签（10 条指标各一个 sparkline）
- [x] 12 个 `spark-cell` class 出现（10 行 + 2 CSS 规则）
- [x] 8 条已回填指标渲染真实折线（`<path d="M..."`）
- [x] 2 条指标显示"积累中"占位（VIX Yahoo 限速漏拉 + SOFR-IORB 派生跳过 cache 回填）
- [x] 阈值带三段（每条折线 3 个 `<rect>`）按 direction 正确着色
  - up 方向（VIX 等）：顶部 RED rgba(239,68,68)
  - down 方向（10Y-2Y）：顶部 GREEN rgba(34,197,94)

### 3.2 本轮新增专项

- [x] sparkline 数据来源：先 cache DB get_series_range，不够 10 个点走主 DB get_series 兜底
- [x] cache DB 路径可注入（测试用 tmp_path），生产用默认 hdbmod.HISTORY_DB_PATH
- [x] 末点蓝色高亮（`<circle cx>` 接近右边缘）
- [x] 占位 SVG 含"积累中 (n/10)"提示文字

### 3.3 回归检查

- [x] pytest 267/267 通过（244 → 267，+23 新测试）
- [x] 现有 source-link / 综合温度计 gauge / 5 维度分组 / chatbot 浮窗都没破
- [x] empty 行（无数据指标）也保留 sparkline 占位 + source 链接

## 4. 看图发现的问题

- chromium 仍没装，没有可视截图。但 curl + grep 数据流完整验证：
  - 8 个真实折线 + 2 个占位 + 三档背景带 + 末点高亮
  - 视觉效果只能等用户在浏览器实际打开 http://127.0.0.1:5050 验证

## 5. 结论

- [x] **PASS** — 数据流完整、HTML 渲染正确、pytest 双绿。
- 用户在浏览器打开后，下一轮（iter 40）做"同环比对比表"前可顺手验视觉效果。

## 6. TODO

- [ ] 等用户网络条件好时一句 `playwright-cli install-browser chromium` 让 visual_check 真截图
- [ ] iter 41 要回头补 VIX 历史数据（绕开 yahoo 限速：分多次小批量拉，或改用 FRED:VIXCLS）
