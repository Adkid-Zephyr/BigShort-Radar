# 上一轮总结

迭代 57(2026-05-17):阈值校准三件套(派生现场计算 + 维度 max + 切点 65→60)。

## 本轮做了

按用户拍板"一轮全做完三件,严格 max",首跑发现"max + 切点 50"会让任一 YELLOW 直接 RED 过敏感,与用户复议改切点 60。

### A. 派生指标回测现场计算

- 新增 `src/backtest/derived.py` 注册三条派生:
  - `vix_term_structure` = `vix_fred / vix3m`
  - `sofr_iorb` = `|sofr_raw - iorb_raw| × 100`(bp)
  - `fra_ois` = `dgs3mo - sofr_raw`
- 改 `src/backtest/score.py::compute_score_for_date`:优先取 name 本身,缺时调 `derived_mod.fetch_derived_value`
- `scripts/backfill_history.py::BACKTEST_EXTRA_TARGETS` 加 4 条原料(vix3m/sofr_raw/iorb_raw/dgs3mo)
- 跑 backfill --backtest --start 2006-01-01:FRED 三条入库 sofr_raw 2027 / iorb_raw 1755 / dgs3mo 5096;VIX3M 仍受 yahoo 限速降级

### B. 维度内最严 max

- `src/compute/risk_score.py::score_from_indicator_values` 把 `group_score = sum/len` 改 `max(items.score)`
- 解决雷曼周 VIX_FRED 36 + TED 3 都触发 RED 但综合分仍 YELLOW 32 的稀释盲区

### C. 切点 65→60

- `SCORE_RED_MIN = 60.0`(原计划 50,首跑发现过敏感后复议改 60)

### D. 三窗口重跑验证

| 窗口 | 天数 | mean | RED 天 | RED 占比 |
|---|---:|---:|---:|---:|
| 2008 雷曼 | 547 | 34.8 | 33 | 6.0% |
| COVID-19 | 488 | 42.9 | 42 | 8.6% |
| 2022 加息 | 546 | 67.1 | 393 | 72.0% |

雷曼/COVID 比例合理(6-9%);2022 RED 占 72% 反映史诗级紧张真实情况(通胀 9% + 史上最快加息 + 英国 LDI 危机),但也暴露**组间稀释**残留(单组 100 加权后只占 12-20% 份额)。

### 测试 & 验证

- pytest 492 → 504(新 derived 12 个用例 + risk_score 加 1 个 max 用例;mixed_yellow 改 GREEN+YELLOW;classify_total 切点 60)
- SUMMARY.md 模板更新,自动生成 iter 57 校准后对比表

## 用户额外要求(本轮内未执行,占位 iter 58)

用户提出做完后必须做"全局复盘 + 期权交易者视角缺口分析",针对未来辅助交易标的(沪深 300 / 上证 50 / 纳指 / 美七姐妹个股期权)。
候选数据清单和需用户协助找的接口已存 `.ralph/iter57_postmortem_pending.md`。
**iter 58 按这条清单做缺口补齐**(原 iter 58 老历史调研后置)。

git iter 56 58a5c3d → 57 待 commit

## 下一轮(iter 58)

阅读 `.ralph/iter57_postmortem_pending.md`,先呈现"自我审视清单"+ "期权视角缺什么" + "数据源候选(免费/需注册)"给用户挑,再 EnterPlanMode 实施。

不要急着写代码 — 用户优先想看"哪些有意义/没意义/缺什么"的判断。
