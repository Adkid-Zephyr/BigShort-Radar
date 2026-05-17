# 上一轮总结

迭代 50（2026-05-17）：风险矩阵热力图 + 综合温度计 2 年时间线（视角 D + E）。

## 本轮做了

- src/web/heatmap.py:
  - build_heatmap_html: 19 指标 × 90 天 × 3 档颜色 plotly Heatmap
  - build_risk_timeline_html: 综合分 730 天走势 + 三档背景带 + 切点水平线
- src/compute/risk_score.py: 加 get_risk_series(conn, days) 取风险分历史
- 新页 /heatmap 与 /timeline，nav 两项激活
- 10 个新测试，pytest 433 → 443

git iter 49 2d4b9c9 → 50 待 commit

## 下一轮（iter 51）
路线图最后一轮：政策对冲对比页 + 阈值校准面板（视角 I + J）。
- /hedge：风险面（VIX/HY OAS）vs 对冲面（WALCL/ON RRP/TGA）并排对比
- /calibration：每条指标历史读数 vs 当时市场表现（需要市场数据 SP500 等，简化版可只显示阈值历史触发率）
- 测试 + push

下一句"继续"将进 iter 51（路线图终点）。
