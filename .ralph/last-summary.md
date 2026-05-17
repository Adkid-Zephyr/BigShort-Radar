# 上一轮总结

迭代 38（2026-05-17）：历史数据 cache DB 基础设施 + akshare 决策方案 B。

## 本轮做了

### A. akshare 引入决策（命中暂停清单）

写 BLOCKED.md 评估 akshare 28 个传染依赖（mini-racer V8 引擎 / lxml / curl_cffi 爬虫栈），用户拍板**方案 B：不引入**，仅用 FRED 能拿到的 3 条中国指标（中国外汇储备 / USDCNY / 中国 10Y）。

**总指标终态从 26 条下调到 19 条**（10 现有 + 政策 3 + 波动率 2 + 融资 1 + 中国 3）。
DECISIONS.md 写入完整 ADR。

### B. 历史 cache DB 骨架（4 个新文件）

- `src/store/history_db.py`（210 行）：独立 cache DB（`data/historical_cache.sqlite`）
  - schema：`history_points` 表 + `idx_hist_name_date` 索引
  - API：`open_history_db` / `upsert_point` / `bulk_upsert` / `get_series_range` / `count_points`
  - 与主 DB 完全隔离，模式参考 `src/store/db.py`
- `src/fetch/history_fetcher.py`（70 行）：通用历史路由器
  - `fetch_history(source, start, end)` 按前缀分发到 fred_client / yf_client
  - 大小写无关、空格容错、派生（含 `,`）拒绝
- `scripts/backfill_history.py`（150 行）：一次性回填脚本
  - `--start` / `--end` / `--years 5` / `--only <name>` 参数
  - 派生指标（含 `/`，或 FRED 前缀含 `-` 如 SOFR-IORB）自动跳过
  - 失败一条不影响其他
- 测试：47 个新用例
  - `tests/test_history_db.py` 17 用例（CRUD / NaN/Inf / idempotent / range 查询）
  - `tests/test_history_fetcher.py` 14 用例（路由 / 大小写 / 边界）
  - `tests/test_backfill_history.py` 16 用例（派生识别 / mock fetcher / --only 过滤）

测试：pytest **244 通过 / 0 失败 / 0 skip**（197 → 244，+47）。

git：iter 37 8295ff8 → iter 38 待 commit。

## 下一轮（iter 39）

Sparkline 90 天微折线（首发异常监测视角）：

1. 在 dashboard 模板每条指标行右边加 SVG 微折线 +/- 阈值带（90 天）
2. 数据来源：`history_db.get_series_range`（如有）+ 主 DB `get_series` 兜底
3. 纯前端 SVG，不引依赖
4. 视觉自检：跑 visual_check.sh（chromium 装好后看图）

注意：iter 38 没真跑 backfill，cache DB 还空。iter 39 实施前需要先用户**真跑一次**：

```bash
.venv/bin/python -m scripts.backfill_history --years 5
```

会调真实 FRED + Yahoo API，拉 8 条非派生指标过去 5 年序列，约 ~12000 行数据。

下一句"继续"将进 iter 39。
