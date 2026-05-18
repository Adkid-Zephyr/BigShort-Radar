# 上一轮总结

迭代 64(2026-05-18):修复首页环型温度计读取过期 risk_scores 快照的问题。

## 用户反馈

用户看到环型温度计里“波动率 / 信用 / 曲线”都是 0,怀疑有问题。

## 排查结论

- **波动率=0 是问题**：首页读的是 `risk_scores` 表旧快照(2026-05-17,score=26.33,波动率=0),而 iter 58-62 补入的 VIX/VIX term/VIX9D/VIX1Y/VVIX/SKEW/PutCall 没有触发重新写 risk_scores。
- **信用=0 正常**：HY OAS=2.76、IG OAS=0.76,都 GREEN。
- **曲线=0 正常**：10Y-2Y=0.5、10Y-3M=0.9,按当前阈值都 GREEN。

实时计算结果:

```text
score=53.5 YELLOW
波动率=100
期权情绪=50
曲线=0
信用=0
流动性=50
跨市场=100
政策=100
中国=100
```

## 本轮做了

### A. 首页温度计改实时计算

`src/web/app.py` 首页 `/`:

- 旧: `risk = rs.get_latest_risk_score(conn)`
- 新: `risk = rs.compute_score(conn, _INDICATOR_REGISTRY)`

并补 `risk["date"]` 为当前 latest 指标最大日期。

`risk_scores` 表继续保留给 `/timeline` 历史页使用。

### B. 测试覆盖 stale 场景

新增 `tests/test_web.py::test_index_gauge_uses_live_risk_not_stale_snapshot`:

- 先写一个旧的全 GREEN risk_scores 快照
- 再写最新 VIX RED
- 断言首页出现 RED + 波动率 100,证明不读旧快照

### C. 测试

pytest 522 → 523 全过。

## 本轮客观自我评价

**对 vision 的贡献度**:⭐⭐⭐⭐⭐
- 监控金融危机维度:温度计是系统第一读数,读旧快照会直接误导风险判断。
- 为大空头交易做准备维度:波动率组目前 SKEW RED/VVIX YELLOW/VIX1Y YELLOW,如果温度计仍显示 0,会错过尾部风险。

**有没有跑偏**:
- 没跑偏。这是产品正确性修复,优先级高于继续加指标。

**坦率失误 / 妥协**:
- 前几轮手动补数据后没有同步重算 risk_scores,导致 dashboard gauge stale。根因是首页依赖存储快照,而不是实时 latest。
- `/timeline` 仍依赖 risk_scores 历史,这没问题;但以后若要 timeline 也最新,应在 daily_fetch 后统一 run_and_store。

**下一轮真正该做的**:
- iter 65 回到原计划:月频 old-history 回测引擎骨架(Shiller/DataHub + FRED AAA/BAA/INDPRO/CPI)。

git iter 63 f590af6 → 64 待 commit
