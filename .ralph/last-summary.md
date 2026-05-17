# 上一轮总结

迭代 40（2026-05-17）：Sparkline 可点击 + 指标详情页 + base.html 多页架构起点。

## 本轮做了

### A. 多页架构基础

- `templates/_base.html` 新建：共享 head/CSS/顶部 nav/chatbot 浮窗/`{% block content %}`
- `templates/index.html` 重写继承 _base，从 394 行减到 ~110 行
- `templates/indicator_detail.html` 新建：plotly 大图 + dl 元信息 + 面包屑

### B. Plotly 大图（详情页）

- 装 plotly 6.7.0（已在 requirements.txt 白名单）
- `src/web/charts.py` 新建：`build_indicator_chart_html(name, label, dates, values, threshold_low, threshold_high, direction)`
  - 主折线 + 末点蓝色高亮
  - 阈值水平线 + 三档区域填色（up 顶 RED / down 顶 GREEN）
  - 工具栏配置 zoom/pan/reset/导出 PNG，去 lasso/select
  - `include_plotlyjs="cdn"` 详情页加载 plotly 3.5.0 CDN

### C. app.py 路由

- 加 `/indicator/<name>` → 渲染 indicator_detail.html
- 加 `_REGISTRY_BY_NAME: Dict[str, ind]` O(1) 索引
- 拆 `_fetch_history_pairs` 返 `(dates, values)` 同时支持 sparkline 和详情页
- 404 路径：未注册 name 走 `abort(404)`

### D. 顶部导航条

5 项：指标（current）+ 事件 / 热力图 / 时间线 / 对冲面（disabled grey 占位，后续 iter 47-51 实现）

### E. Sparkline 可点击

主 dashboard 每条 sparkline 包成 `<a href="/indicator/<name>" class="spark-link">` + `:hover` 提亮

### F. 测试

- `tests/test_charts.py` 10 个用例（占位 / 阈值线 / 方向 / 自定义 height）
- `tests/test_indicator_detail_page.py` 11 个用例（200/404/breadcrumb/dl/plotly/source_url/nav）
- pytest **288 通过 / 0 失败 / 0 skip**（267 → 288，+21）

### G. 文档同步 6 条

- INDICATORS.md：不动
- DECISIONS.md：iter 40 完整 ADR
- README.md：tests 数 197 → 288
- HANDOFF.md：不动
- THESIS.md：不动
- PLAN.md：iter 40 标 [x]，路线图后置（同环比表 → iter 41，原 50 → 51）

### H. 实测验证

```
curl http://127.0.0.1:5050/                   → HTTP 200，10 个 spark 链接
curl http://127.0.0.1:5050/indicator/vix      → HTTP 200，含 plotly CDN script
curl http://127.0.0.1:5050/indicator/hy_oas   → 36KB，含 786 个 plotly y 数据点（5 年历史）
curl http://127.0.0.1:5050/indicator/none     → HTTP 404
```

git：iter 39 f5cf49f → iter 40 待 commit。

## 下一轮（iter 41）

**同比 / 环比对比表**（行内增强）：

- 行里加 4 列：今日 / 上周 / 上月 / 上季度 + 4 列变化百分比
- 数据：history_db.get_series_range 取那几个日期点的最近值
- 颜色：恶化方向用红字（结合 direction 判断"恶化"是上升还是下降）
- `src/web/comparisons.py` 新模块：纯函数 `lookback_summary(history, today, lookback_days)` 返 dict {value, pct_change, deteriorate}
- 模板表格加列（6 列变 10 列，要重排版）
- 测试：mock history 数据 + e2e dashboard 含同环比

下一句"继续"将进 iter 41。
