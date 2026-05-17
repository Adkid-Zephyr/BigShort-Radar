"""历史回测模块（iter 52 起）。

把 19+ 条指标的阈值与综合温度计算法放到 2007-2024 真实历史数据上反向跑，
看综合分能否在已知崩盘前 N 周提前发出 RED 警告。

服务于 THESIS §6.1：所有阈值与权重的"科学校准"基础。

入口：
- src.backtest.engine.backtest_window(start, end, registry) — 按日跑综合分
- src.backtest.score.compute_score_for_date — 单日综合分（forward-fill 取最近值）
- src.backtest.registry.BACKTEST_INDICATORS — 含 vix_fred/libor_ois 双轨
"""
