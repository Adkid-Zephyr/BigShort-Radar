# 上一轮总结

迭代 42（2026-05-17）：Z-score 列（异常监测视角 B）。

## 本轮做了

- `src/web/zscore.py`：纯函数 compute_zscore 算 z + percentile + extreme + n
- `_build_rows` 拉 5 年（days=1825）long_values 单独算 z（不复用 120 天 sparkline）
- 模板加 Z 列（|z|>2 + 方向匹配 → 红字 bad，hover 提示百分位+n）
- _base.html 加 .zcol CSS
- 17 个新测试

测试：pytest 310 → 327（+17）

实测：jp_10y +2.6σ 99 分位标红（历史最高 = 危险信号）；其他多数 ±1σ 正常

git：iter 41 e8e9728 → iter 42 待 commit

## 下一轮（iter 43）

加速度（5/20 天斜率）列：
- src/web/acceleration.py 纯函数 compute_slope(values, window) 返 (slope_per_day, vs_long_term)
- 比较短期斜率（5 天）和长期斜率（20 天）：短>长 = 加速恶化
- 模板加 Δ 列
- 测试 + push

下一句"继续"将进 iter 43。
