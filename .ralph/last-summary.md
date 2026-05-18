# 上一轮总结

迭代 63(2026-05-18):1970s/1929 老历史数据源调研。

## 本轮做了

### A. 输出调研文档

新增 `data/backtest_results/OLD_HISTORY_SOURCES.md`。

### B. 1970s 结论

1970s 可以做,且主要靠 FRED 足够:

- DGS10(1962 日)
- TB3MS(1934 月)
- DTB3(1954 日)
- AAA / BAA(1919 月)
- FEDFUNDS(1954 月)
- CPIAUCSL(1947 月)
- INDPRO(1919 月)
- UNRATE(1948 月)
- M1/M2(1959 月)
- OILPRICE(1946 月,discontinued 但历史可用)

推荐窗口:
- 1968-1970
- 1973-1975
- 1978-1982

### C. 1929 结论

1929 不应硬跑现代 22 条指标,只能做月频代理:

- DataHub/Shiller `s-and-p-500` CSV(1871 月,SP500/Dividend/Earnings/CPI/Long Interest Rate/CAPE)
- FRED AAA/BAA(1919 月)算 Baa-Aaa 信用利差
- FRED INDPRO(1919 月)看经济下行

若要 DJIA 日频 1929:
- MeasuringWorth DJA 页面有 1885/1896+ 日收盘
- 但无稳定 CSV/API
- 需要用户人工导出或确认是否允许写表单爬取

### D. 决策

old-history 不应混入现有日频综合温度计,应单独做 `monthly old-risk score`,避免伪精确。

### E. 测试

pytest 522/522 通过。本轮纯文档/调研,没有代码变更。

## 本轮客观自我评价

**对 vision 的贡献度**:⭐⭐⭐⭐
- 监控金融危机维度:明确 1970s/1929 真实可用数据边界,避免为了回测而造假精度。
- 为大空头交易做准备维度:能把危机剧本从 2008/2020/2022 扩展到 1970s/1929,但必须诚实用代理。

**有没有跑偏**:
- 没跑偏。调研不是堆指标,是为历史校准打基础。

**坦率失误 / 妥协**:
- 本轮没有实现代码,只完成调研。1929 日频需要用户人工数据,无法自动解决。
- 如果用户坚持日频 1929,需要后续明确授权抓 MeasuringWorth 或找付费/公开 CSV。

**下一轮真正该做的**:
- iter 64:月频 old-history 回测引擎骨架。先接 DataHub/Shiller CSV + FRED AAA/BAA/INDPRO/CPI,跑 1928-1933 月频代理,输出 OLD_HISTORY_SUMMARY.md。

git iter 62 d6ffbea → 63 待 commit
