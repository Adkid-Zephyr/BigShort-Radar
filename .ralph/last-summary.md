# 上一轮总结

迭代 49（2026-05-17）：5 剧本检测器（THESIS §3.2 核心 + 视角 G）。

## 本轮做了

- src/web/scenarios.py: 5 剧本定义 + evaluate_scenarios 三档（active/watch/quiet）
  - A 美元荒：DXY/USDJPY/SOFR-IORB/ON RRP 4 条规则 min_match=3
  - B 国债基差：SOFR-IORB/yield_curve_10y2y/WALCL min_match=2
  - C 日本 carry：USDJPY/jp_10y/china_fx_reserves min_match=2
  - D AI 泡沫：vix_term_structure/vvix/skew min_match=2
  - E 信用滞后崩：hy_oas/ig_oas min_match=2
- 主 dashboard 顶部加剧本卡片网格（响应式，红/黄/灰 边色）
- _base.html 加 .scenarios CSS
- 15 个新测试，pytest 433

git iter 48 d79dca2 → 49 待 commit

## 下一轮（iter 50）
风险矩阵热力图 + 综合温度计 2 年时间线（两个新页）：
- /heatmap：横轴日期（最近 90 天）× 纵轴指标，每格按 level 着色
- /timeline：综合分 2 年走势 plotly
- nav 中"热力图""时间线"激活
- 测试 + push

下一句"继续"将进 iter 50。
