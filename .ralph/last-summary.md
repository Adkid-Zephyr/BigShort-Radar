# 上一轮总结

迭代 61(2026-05-18):VVIX/SKEW 从 yahoo 切 CBOE 官方 CSV,补齐 dashboard 尾部风险指标空白。

## 本轮做了

### A. VVIX/SKEW 数据源切换

- `src/compute/indicators/vvix.py`
  - `yf_client.fetch_close("^VVIX")` → `cboe_client.fetch_index_history("VVIX")`
  - `SOURCE = "YF:^VVIX"` → `SOURCE = "CBOE:VVIX_History.csv"`
  - 阈值 90/120 不变

- `src/compute/indicators/skew.py`
  - `yf_client.fetch_close("^SKEW")` → `cboe_client.fetch_index_history("SKEW")`
  - `SOURCE = "YF:^SKEW"` → `SOURCE = "CBOE:SKEW_History.csv"`
  - 阈值 130/145 不变

### B. CBOE client 增强

- `src/fetch/cboe_client.py::fetch_index_history`
  - 原本支持 `DATE,OPEN,HIGH,LOW,CLOSE`
  - 新增支持 CBOE 旧式 `DATE,VVIX` / `DATE,SKEW` 两列结构
  - value_col = CLOSE if exists else symbol.upper()

### C. 测试更新

- `tests/test_volatility_indicators.py`
  - source 断言改 CBOE
  - mock 从 yf_client 改 cboe_client
- pytest 520/520 通过

### D. 真实补数据

- VVIX:写入主 DB 11 条,latest 2026-05-15 value=92.94 source=CBOE:VVIX_History.csv
- SKEW:写入主 DB 11 条,latest 2026-05-15 value=145.77 source=CBOE:SKEW_History.csv

### E. 文档同步

- `INDICATORS.md` 加 vvix/skew 两条指标卡
- `DECISIONS.md` 加 iter 61 ADR
- `README.md` 指标表与 iter 61 说明更新
- `HANDOFF.md` 更新基线
- `PLAN.md` 标记 iter 61 完成

## 本轮客观自我评价

**对 vision 的贡献度**:⭐⭐⭐⭐
- 监控金融危机维度:VVIX/SKEW 是尾部风险和反身性关键指标,修掉 yahoo 限速空白后 dashboard 可信度提升。
- 为大空头交易做准备维度:VVIX 衡量"恐慌本身的波动",SKEW 衡量左尾保险溢价,两者直接影响买 put/put spread 的时机与贵贱判断。

**有没有跑偏**:
- 没跑偏。继续沿着期权交易者核心数据和可靠源修复推进。

**坦率失误 / 妥协**:
- 只补了最近 2026-05-01 起的 11 条主 DB 数据;CBOE CSV 历史全量可拉,但本轮为了快速修 dashboard 没回填 2006-2026 全历史到主 DB/cache。
- SKEW latest 145.77 直接 RED,说明当前 tail risk 定价已较高,后续简报和剧本要关注。

**下一轮真正该做的**:
- iter 62 建议把 Put/Call 拆成 total/index/equity 三条,或先讨论是否新建 `期权情绪` 维度。因为 Put/Call 与 VIX/SKEW 不完全同类,放在波动率组会被 max 触顶放大。

git iter 60 4a5fb67 → 61 待 commit
