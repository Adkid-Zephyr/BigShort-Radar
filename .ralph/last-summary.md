# 上一轮总结

迭代 43（2026-05-17）：加速度 Δ 列（视角 C）。

- src/web/acceleration.py: linear_slope（最小二乘）+ compute_acceleration（短 5d / 长 20d，结合 direction 判加速恶化）
- _build_rows 注入 acceleration 字段
- 模板加 Δ 列（↗ 加速恶化红字 / · 不加速 / —）
- 14 个新测试，pytest 327 → 341

实测：DXY 短斜率 0.66/d > 长斜率 0.31/d → ↗ 红字（美元加速走强）

git iter 42 def6104 → 43 待 commit

## 下一轮（iter 44）
政策反应维度 3 条：WALCL / ON RRP / TGA。
- src/compute/indicators/walcl.py / on_rrp.py / tga.py（FRED 系列）
- 阈值待 ADR：WALCL/TGA 是绝对值（万亿美元级）+ 方向 down=减少=QT=收紧 / ON RRP 方向 down=资金离开=流动性恶化
- 加进 _INDICATOR_REGISTRY + _GROUP_ORDER 加"政策"
- 跑一次 backfill_history --only walcl 等
- 测试

下一句"继续"将进 iter 44。
