# 上一轮总结

迭代 22（2026-05-15）：HY OAS 上线，第四条指标，dashboard 加入信用维度。

本轮做了：
- DECISIONS.md 追加 ADR：HY OAS 阈值 GREEN<4 / YELLOW 4–8 / RED>8（up 方向）
  历史分位依据：平静期 3–4%（2017、2021）、紧张期 5–7%（2022 末）、危机期 ≥10%（2008=18 / 2020 春=11）
- INDICATORS.md：新增 hy_oas 完整条目，P1 占位列表标记 ✅
- src/compute/indicators/hy_oas.py：FRED:BAMLH0A0HYM2 → fetch + classify + upsert
  - NAME=hy_oas，DIRECTION=up，LOW=4.0 HIGH=8.0
  - 直接用 store helper（iter 21 抽出来的 `upsert_series_from_pandas`），文件 60 行，最简
- tests/test_hy_oas.py：5 classify + 4 fetch_and_store
- src/web/app.py：注册 "HY OAS 高收益债利差"
- scripts/daily_fetch.py：FETCHERS 加 hy_oas

测试情况：
- pytest 共 97 通过 / 0 失败 / 0 skip（+9）
- helper 抽象的优势已显现：本指标只新增 60 行代码就完成功能 + 测试

git：iter 21 ebb7f3c → iter 22 待 commit。

下一项 PLAN 顶上的 `[ ]`：
- **P1 第四项：IG OAS（FRED: BAMLC0A0CM，投资级利差）**

实现路径（用 helper，结构与 hy_oas 同款）：
- 新文件 `src/compute/indicators/ig_oas.py`，方向 up
- 阈值 ADR（推荐路线下一轮直接落）：IG OAS 历史分位远窄于 HY——平静期 0.8–1.5%（2021）、紧张期 2–3%（2022 末）、危机期 ≥5%（2008=6.5 / 2020 春=4.0）。推荐 GREEN <1.5 / YELLOW 1.5–3 / RED >3
- INDICATORS.md 加完整条目；DECISIONS.md 备案
- web/app.py 与 daily_fetch.py 同步注册

按用户"一直走推荐路线"指令，下一句"继续"将直接按上述方案落地 iter 23。
