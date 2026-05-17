# 上一轮总结

迭代 46（2026-05-17）：FRA-OIS 代理 + 中国维度 3 条全部上线。

## 本轮做了

### 4 个新 indicator 模块
- fra_ois.py: FRED:DGS3MO - FRED:SOFR 派生，up，阈值 0.10/0.30 百分点
- china_fx_reserves.py: FRED:TRESEGCNM052N down，阈值 3.0T/3.1T 美元
- usdcny.py: FRED:DEXCHUS up，阈值 7.10/7.30
- china_10y.py: FRED:IRLTLT01CNM156N down，阈值 2.0/2.5

### 注册同步
- _INDICATOR_REGISTRY 加 4 条（FRA-OIS 入流动性，3 条入"中国"）
- _GROUP_ORDER 加"中国"
- daily_fetch FETCHERS / backfill TARGETS 同步
- _GROUP_WEIGHTS 再平衡 → 7 维度（含中国 10%）

### 测试 + 实测
- 25 个新测试
- pytest 400/400 通过（375 → 400）
- backfill：USDCNY 1246 日值，china_fx_reserves 57 月值，china_10y FRED 空（月值数据偶有空缺）
- daily_fetch 跑 19 个 fetcher 0 失败
- **综合分 GREEN 20.83 → YELLOW 26.33**（中国维度纳入后切换）

git iter 45 → 46 待 commit

## 下一轮（iter 47/48）
中国维度 3 条已合并到 iter 46。原 iter 47 占位用 [x] 标完成。
直接进 iter 48：**异常事件流**（30 天倒序）：
- 新页面 `/events`，扫近 30 天 history pairs 找"翻档 / 突破阈值 / 多指标同时走阔"事件
- 模板继承 _base.html，nav 中"事件"项激活
- 测试

下一句"继续"将进 iter 48。
