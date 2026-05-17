# Visual Check Report — iter 40

## 1. 改动摘要

- 改了：
  - `templates/_base.html` 新建（共享布局 + nav + 通用 CSS + chatbot 浮窗）
  - `templates/index.html` 大幅简化（继承 _base + sparkline 包 anchor 跳详情）
  - `templates/indicator_detail.html` 新建（plotly 大图 + 元信息 dl + 面包屑）
  - `src/web/charts.py` 新建（plotly to_html，CDN 共享，三档区域填色）
  - `src/web/app.py` 加路由 `/indicator/<name>` + `_REGISTRY_BY_NAME` + `_fetch_history_pairs`
- 期望 UI 看到：
  - 主 dashboard 顶部出现"指标 / 事件 / 热力图 / 时间线 / 对冲面"导航条（事件/热力图等灰色禁用，待后续 iter 实现）
  - sparkline 鼠标悬停变亮，点击跳指标详情页
  - 详情页含面包屑 / 标题 / 元信息 dl / plotly 大图（可缩放可拖动可导出 PNG）

## 2. 自检命令

```bash
bash scripts/visual_check.sh
# chromium 仍未装 → graceful 退出 rc=1
```

替代：curl + grep + pytest 三重验证。

## 3. 看图判断

### 3.1 必查项

- [x] 主 dashboard 渲染含 page-nav class（grep 多处 `.page-nav` CSS + `class="current"`）
- [x] 10 条指标 sparkline 全部包了 `<a href="/indicator/<name>">`（curl 验 10 个不同 href）
- [x] 详情页 `/indicator/vix` HTTP 200（33014 字节，比 dashboard 32KB 略大因含 plotly 数据）
- [x] 详情页 `/indicator/nonexistent` HTTP 404（abort 生效）
- [x] 详情页加载 `cdn.plot.ly/plotly-3.5.0.min.js`（plotly CDN）
- [x] HY OAS 详情页内嵌 786 个 plotly y 数据点（5 年回填全量加载）

### 3.2 本轮新增专项

- [x] base.html 提取通用 CSS / chatbot 浮窗 / 顶部 nav / `{% block content %}`
- [x] index.html 从 394 行减到 ~110 行（继承复用）
- [x] indicator_detail.html 完整 dl 结构：当前值 / 更新日期 / 阈值 / 方向 / 分组 / 数据源
- [x] charts.py 三档填色（up 顶 RED / down 顶 GREEN）+ 阈值水平线 + 末点高亮
- [x] active_page 高亮当前 nav 项（首页和详情页都标 "index" 当前栏）

### 3.3 回归

- [x] pytest 288/288 通过（267 → 288，+21 新测试）
- [x] iter 39 sparkline 仍正常渲染（grep 8 个 path + 2 个占位）
- [x] iter 35/36 source-link 跳官方页仍工作

## 4. 看图发现的问题

- chromium 仍没装，没有截图。但功能层面 curl + grep + pytest 都通过。
- 用户在浏览器实际打开 http://127.0.0.1:5050/ 验证：sparkline 是否能点击跳转 + plotly 大图是否可缩放拖动。

## 5. 结论

- [x] **PASS** — 数据流完整、HTML 渲染正确、双绿。
- 用户实际浏览器交互体验等用户回来验证。

## 6. TODO

- [ ] chromium 装好后回头 visual_check 真截图
- [ ] iter 41 加同环比对比表，行内增强
