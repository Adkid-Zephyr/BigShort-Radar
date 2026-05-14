# 上一轮总结

迭代 2（2026-05-15）：响应用户新指令"延后所有需注册 API key 的指标"，重排 PLAN.md + 留痕 DECISIONS.md。

本轮做了：
- PLAN.md 顶部加"API key 延后规则"说明段
- P0 中 `fred_client.py`、`yield_curve.py` 及其测试后缀加 `⏸ 待 API key`，`tests/test_fetch.py` 注明仅先覆盖 yf
- P1 中 `10Y-3M / HY OAS / IG OAS / SOFR-IORB / FRA-OIS` 一并加 `⏸ 待 API key`
- P0 新增决策项："首条上线指标改用什么数据源"，候选 VIX(yfinance) 或等 FRED key 后做 10Y-2Y，留给用户拍板
- DECISIONS.md 追加 2026-05-15 一条"FRED 等数据源延后"决议

测试情况：
- 本轮纯文档/计划重排，无 src 代码改动，pytest 不适用

下一轮建议：
- PLAN.md 顶上下一项是 `创建 requirements.txt`，本身不依赖任何 key，可直接做
- 中间会碰到那个新增的"决策"项，到时候停下等用户拍板

未决问题：
- 等用户决定首条上线指标走 VIX(yfinance) 还是等 FRED key 后做 10Y-2Y
