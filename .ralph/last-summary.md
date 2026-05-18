# 上一轮总结

迭代 59(2026-05-18):VIX 期限结构从 yahoo 切 FRED,并补齐 VIX/VIX3M 主 DB 历史数据。

## 本轮做了

### A. VIX 期限结构数据源切换

- `src/compute/indicators/vix_term_structure.py`
  - `yf_client.fetch_close("^VIX")` / `yf_client.fetch_close("^VIX3M")`
  - → `fred_client.fetch_series("VIXCLS")` / `fred_client.fetch_series("VXVCLS")`
  - `SOURCE = "YF:^VIX/^VIX3M"` → `SOURCE = "FRED:VIXCLS/VXVCLS"`
  - 阈值 0.95 / 1.0 不变

### B. 错误草稿主动删除

本来计划顺手加 VIX9D/VIX1Y,但真实验证发现:

- FRED:VIXCLS ✅ 可用
- FRED:VXVCLS ✅ 可用
- FRED:VXSTCLS ❌ 不存在
- FRED:VXMTCLS ❌ 不存在

因此删除 `vix9d.py` / `vix1y.py` 草稿,不把错误数据源接入系统。VIX9D/VIX1Y 改下一轮查 CBOE/官方 CSV 源。

### C. 测试更新

- `tests/test_vix_term_structure.py`
  - mock 从 `yf_client.fetch_close` 改 `fred_client.fetch_series`
  - 新增 `test_source_is_fred`,防止后续误回退 yahoo
  - source 断言改 `FRED:VIXCLS/VXVCLS`
- pytest 506/506 通过

### D. 真实补数据

用本机 FRED key 回填主 DB:

- `vix`: inserted 1629, rows 1629, latest 2026-05-14 value=17.26 source=FRED:VIXCLS
- `vix_term_structure`: inserted 1600, rows 1600, latest 2026-05-14 value=0.8278 source=FRED:VIXCLS/VXVCLS

### E. 文档同步

- `DECISIONS.md` 加 iter 59 ADR
- `README.md` 指标表 VIX 期限结构 source 改 FRED `VIXCLS/VXVCLS`,新增 iter 59 说明
- `INDICATORS.md` VIX 期限结构数据源/计算口径同步
- `HANDOFF.md` 更新 iter 59 实时基线
- `PLAN.md` 标记 iter 59 完成,iter 60 改 CBOE Put/Call Ratio 或 VIX9D/VIX1Y 官方源调研

## 本轮客观自我评价

**对 vision 的贡献度**:⭐⭐⭐⭐
- 监控金融危机维度:VIX 期限结构(backwardation)是危机定价最直观指标之一,这轮把它从不稳定 yahoo 源切到稳定 FRED 源,并补齐 1600 条主 DB 历史。
- 为大空头交易做准备维度:VIX/VIX3M ratio 对期权交易有直接含义——判断近月恐慌 vs 中期不确定性,决定短期期权是否已经过贵。

**有没有跑偏**:
- 没跑偏。没有硬加 VIX9D/VIX1Y,发现 FRED series 不存在后主动删掉草稿。

**坦率失误 / 妥协**:
- 一开始错误假设 FRED 有 VXSTCLS/VXMTCLS,实际不存在。好在真实验证及时拦住,没有把坏数据源 commit。
- 本轮没有解决 VVIX/SKEW 空白;它们仍需 CBOE 直接源。

**下一轮真正该做的**:
- iter 60 做 CBOE Put/Call Ratio 或查 VIX9D/VIX1Y 官方 CSV 源。优先 Put/Call Ratio,因为这是期权交易者每天真正看的资金情绪指标。

git iter 58 0219e3c → 59 待 commit
