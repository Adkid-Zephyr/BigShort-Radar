# 上一轮总结

迭代 60(2026-05-18):期权交易者核心数据补齐 — CBOE Put/Call + VIX9D/VIX1Y。

## 本轮做了

### A. 新增 CBOE public fetch client

- `src/fetch/cboe_client.py`
  - `fetch_index_history(symbol,start,end)`:拉 `https://cdn.cboe.com/api/global/us_indices/daily_prices/{SYMBOL}_History.csv`,解析 `DATE,OPEN,HIGH,LOW,CLOSE`,取 CLOSE
  - `fetch_put_call_ratios()`:解析 CBOE US Options Daily Market Statistics 页面 Next.js 内嵌 ratios JSON
  - 不引入新依赖,只用 requirements 已有的 requests/pandas

### B. 新增三条期权交易者指标

1. `vix9d`
   - source `CBOE:VIX9D_History.csv`
   - 阈值 20/32,方向 up
   - 用来监控短端事件风险(FOMC/NFP/财报/地缘冲击)

2. `vix1y`
   - source `CBOE:VIX1Y_History.csv`
   - 阈值 20/30,方向 up
   - 用来区分短期事件恐慌 vs 全期限危机定价

3. `put_call_total`
   - source `CBOE:US_OPTIONS_DAILY_MARKET_STATISTICS`
   - 阈值 0.85/1.15,方向 up
   - 当前快照,历史靠 daily_fetch 每天累积
   - caveat:Put/Call 有反向指标属性,本系统先按危机监控方向处理

### C. 接入全链路

- `scripts/daily_fetch.py` 加 3 个 fetcher
- `src/web/app.py` `_INDICATOR_REGISTRY` 加 3 条,group=波动率
- `src/fetch/history_fetcher.py` 支持 `CBOE:<SYMBOL>_History.csv`
- `scripts/backfill_history.py` 加 vix9d/vix1y target(Put/Call 无历史源,不 backfill)
- `src/web/source_links.py` 支持 CBOE index dashboard / daily market stats 链接

### D. 真实验证

- VIX9D:写入主 DB 11 条,latest 2026-05-15 value=16.37
- VIX1Y:写入主 DB 11 条,latest 2026-05-15 value=24.04
- Put/Call total:写入今日 1 条,value=0.93

### E. 测试

新增:
- `tests/test_cboe_client.py`
- `tests/test_vix9d_vix1y.py`
- `tests/test_put_call_total.py`

pytest 506 → 520 全过。

### F. 文档同步

- `INDICATORS.md` 加三条指标卡
- `DECISIONS.md` 加 iter 60 ADR
- `README.md` 指标表与 iter 60 说明更新
- `HANDOFF.md` 基线更新到 22 条 / 7 维度
- `PLAN.md` iter 60 标记完成

## 本轮客观自我评价

**对 vision 的贡献度**:⭐⭐⭐⭐⭐
- 监控金融危机维度:VIX9D/VIX1Y 给出短端 vs 长端波动率曲线,比单一 VIX 更能区分"事件恐慌"和"全期限危机定价"。
- 为大空头交易做准备维度:Put/Call Ratio 是期权交易者每天看的资金情绪指标;VIX9D/VIX1Y 直接服务纳指/七姐妹/指数期权的期限选择。

**有没有跑偏**:
- 没跑偏。本轮不是 UI,也不是宏观慢指标,而是直接补期权交易者核心数据。

**坦率失误 / 妥协**:
- Put/Call Ratio 当前只能从 CBOE 页面解析当日快照,没有公开历史 API/CSV。页面结构变化会导致解析失败,已用测试覆盖当前结构。
- Put/Call Ratio 作为风险指标有反向解释属性,不能机械地"越高越空"。下一轮如发现噪声大,应拆到 `期权情绪` 独立 group,不要直接挤压波动率维度。

**下一轮真正该做的**:
- iter 61 二选一:
  1. CBOE VVIX/SKEW 直拉,彻底摆脱 yahoo 限速;
  2. Put/Call 拆成 total/index/equity 三条,区分指数保护 vs 个股追涨/恐慌。

当前推荐 1:先修 VVIX/SKEW 空白,因为这俩已经在 dashboard 却经常没数据。

git iter 59 7fa5002 → 60 待 commit
