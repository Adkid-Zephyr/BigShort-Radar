# 上一轮总结

迭代 48（2026-05-17）：异常事件流（首个新 page，视角 F）。

## 本轮做了

- src/web/events.py: detect_indicator_events 三类（翻档/突破/突变）+ merge_events 倒序
- 新页 /events 路由 + templates/events.html
- nav "事件"项激活（current 高亮 / disabled 灰色 → 蓝色可点击）
- _base.html 加 event-alert/warn/info 分色 CSS + kind emoji 颜色
- 18 个新测试

测试：pytest 400 → 418

git iter 46 22a433b → 48 待 commit（iter 47 已并入 46）

## 下一轮（iter 49）
组合信号告警 + 5 剧本检测器：
- src/web/scenarios.py：5 个崩盘剧本规则化
  - A 美元荒：USDJPY 高 + DXY 高 + SOFR-IORB 高 + ON RRP 低 同时
  - B 国债基差：SOFR 突变 + ...（暂无 CFTC 数据，简化条件）
  - C 日本 carry: USDJPY 突破 + 日本 10Y 上升
  - D AI 泡沫: VIX 期限结构 backwardation + VVIX 高（部分依赖未回填）
  - E 信用滞后崩: HY OAS 走阔 + IG OAS 走阔 + 同步发生
- 主 dashboard 顶部加 "活跃剧本" 横条
- 测试

下一句"继续"将进 iter 49。
