# 上一轮总结

迭代 62(2026-05-18):新增“期权情绪”维度,把 Put/Call 从波动率拆出来,并拆成 total/index/equity 三条。

## 本轮做了

### A. 新增两条 Put/Call 子指标

- `src/compute/indicators/put_call_index.py`
  - 取 CBOE daily ratios 的 `index`
  - 阈值 0.90/1.30
  - 更接近机构/组合层面的指数保护需求

- `src/compute/indicators/put_call_equity.py`
  - 取 CBOE daily ratios 的 `equity`
  - 阈值 0.55/0.85
  - 更容易混入个股/散户/财报交易噪声,但和 index 对照有意义

### B. 新增第 8 维:期权情绪

- `put_call_total` group 从 “波动率” 改 “期权情绪”
- `put_call_index` / `put_call_equity` 也归入 “期权情绪”
- `src/web/app.py` `_GROUP_ORDER` 加 `期权情绪`,放在波动率后

### C. 风险权重重平衡

`src/compute/risk_score.py`:

- 曲线 20 → 18
- 信用 20 → 18
- 流动性 14 → 13
- 波动率 12 → 10
- 期权情绪 新增 8
- 跨市场 14 → 13
- 政策 10 不变
- 中国 10 不变

总和仍 100。

理由:期权情绪对交易很重要,但 Put/Call 噪声比 VIX/SKEW 更大,所以权重低于波动率/信用/曲线。

### D. 接入全链路

- `daily_fetch.py` 加 index/equity fetcher + briefing registry
- `web/app.py` 加 registry + source fallback
- `tests/test_put_call_total.py` 加 index/equity 写库和 classify
- `tests/test_risk_score.py` / `tests/test_web.py` 同步权重/组顺序

### E. 真实验证

写入主 DB:

- put_call_total:2026-05-18 value=0.93
- put_call_index:2026-05-18 value=1.03
- put_call_equity:2026-05-18 value=0.59

### F. 测试

pytest 520 → 522 全过。

## 本轮客观自我评价

**对 vision 的贡献度**:⭐⭐⭐⭐
- 监控金融危机维度:把期权市场成交情绪从隐含波动率中拆出,避免 Put/Call 噪声污染波动率维度。
- 为大空头交易做准备维度:index put/call 可以看机构指数保护需求,equity put/call 可以看个股期权情绪,比 total 单一数字有更强解释力。

**有没有跑偏**:
- 没跑偏。这轮没有加 UI,而是修正指标归类和权重,减少 iter 57 max 算法的副作用。

**坦率失误 / 妥协**:
- Put/Call 三条仍只有当前快照,没有历史回填。CBOE 页面目前没公开历史 CSV/API,历史只能靠 daily_fetch 每天累积。
- 阈值是经验值,后续至少积累 3-6 个月后要回看是否过敏感。

**下一轮真正该做的**:
- 可以暂缓继续加期权数据,转回主线:1970s/1929 老历史数据接口调研;或者做仓位建议映射(综合分→风险敞口/对冲预算/现金)。

git iter 61 9ff632d → 62 待 commit
