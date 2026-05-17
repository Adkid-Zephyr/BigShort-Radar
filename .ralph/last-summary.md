# 上一轮总结

迭代 45（2026-05-17）：波动率结构 2 条 VVIX/SKEW。

- vvix.py: YF:^VVIX up 90/120
- skew.py: YF:^SKEW up 130/145
- 注册到 web/daily_fetch/backfill
- 13 个新测试，pytest 375

**已知**：Yahoo 限速（与 VIX 同），5 年 backfill 失败。VVIX/SKEW 现"积累中"，daily_fetch 每天单点累积。

git iter 44 c22c24b → 45 待 commit

## 下一轮（iter 46）

FRA-OIS 代理 + 中国维度 3 条：
- 新建 fra_ois.py：派生指标（FRED:DGS3MO - FRED:SOFR），DECISIONS ADR 解释代理选择
- 新建 china_fx_reserves.py / usdcny.py / china_10y.py
- group "中国" 加进 _GROUP_ORDER，权重再调
- 测试 + push

下一句"继续"将进 iter 46。
