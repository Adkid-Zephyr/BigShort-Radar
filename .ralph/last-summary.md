# 上一轮总结

迭代 58(2026-05-18):VIX 主流程切 FRED:VIXCLS,修复 dashboard 核心波动率指标受 yahoo 限速导致"积累中"的问题。

## 本轮做了

### A. VIX 数据源切换

- `src/compute/indicators/vix.py`
  - `yf_client.fetch_close("^VIX")` → `fred_client.fetch_series("VIXCLS")`
  - `SOURCE = "YF:^VIX"` → `SOURCE = "FRED:VIXCLS"`
  - `TICKER` → `SERIES_ID`
  - 阈值 20/30 不变,方向 up 不变

### B. 测试更新

- `tests/test_vix.py`
  - mock 目标从 `yf_client.fetch_close` 改 `fred_client.fetch_series`
  - 新增 `test_source_is_fred`,防止后续误回退 yahoo
  - source 断言改 `FRED:VIXCLS`
- `tests/test_visual_check.py`
  - 仓库已 private 后允许同步截图/数据库,原"visual_check 不进 git"测试过时
  - 改为断言 `.env` / `.ralph/.token` / `.ralph/loop_runs.log` 仍 gitignored

### C. 真实验证

用本机 FRED key 跑:

```bash
vix.fetch_and_store(conn, start="2026-05-01")
```

结果:
- inserted 10
- main DB vix rows=342
- latest 2026-05-14 value=17.26 source=FRED:VIXCLS

### D. 文档同步

- `DECISIONS.md` 加 iter 58 ADR
- `README.md` 指标表 VIX source 改 FRED `VIXCLS`,新增 iter 58 数据源稳定性说明
- `INDICATORS.md` 模板示例同步 FRED:VIXCLS
- `HANDOFF.md` 更新 iter 58 实时基线
- `PLAN.md` 标记 iter 58 完成,iter 59 后移期权交易者数据补齐

### 测试

- pytest 505/505 通过

## 本轮客观自我评价

**对 vision 的贡献度**:⭐⭐⭐⭐
- 监控金融危机维度:VIX 是最核心的市场恐慌指标,从不稳定 yahoo 源切到 FRED 稳定源,减少 dashboard 空白和误判。
- 为大空头交易做准备维度:VIX 是 SPX/QQQ/七姐妹期权 IV 环境变量,有直接交易意义。

**有没有跑偏**:
- 没跑偏。这不是堆指标,而是修掉一条核心指标的数据源可靠性问题。

**坦率失误 / 妥协**:
- 只修了 VIX,没有同时修 VIX3M/VVIX/SKEW。保持一轮一件事是对的,但 dashboard 仍会有 VIX3M/VVIX/SKEW 空白。
- 主 DB 写了 10 条新 VIX 数据,已跟随 private 仓库数据同步。

**下一轮真正该做的**:
- iter 59 优先做 VIX3M 从 yahoo `^VIX3M` 切 FRED `VXVCLS`,然后加 VIX9D(FRED:VXSTCLS) / VIX1Y(FRED:VXMTCLS) 或 CBOE Put/Call Ratio。继续补期权交易者真正关心的数据,不要再做 UI。

git iter 57 fb08361 → 58 待 commit
