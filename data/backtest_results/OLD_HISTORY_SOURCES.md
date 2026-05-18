# 老历史回测数据源调研（iter 63）

> 目标：为 1970s 滞胀期 / 1929 大萧条期做历史回测准备。
> 约束：不引入新依赖、不改 SQLite schema、不调付费 API。可用 FRED / CBOE / Shiller/DataHub / 用户人工取数。

## 结论摘要

### 1970s（可直接做，FRED 足够）

1970s 不需要用户人工找太多数据。FRED 覆盖了主要宏观压力代理：

| 现代理 | FRED series | 起始 | 频率 | 可替代当前指标 |
|---|---|---:|---|---|
| 10Y 长债收益率 | `DGS10` | 1962-01-02 | 日 | 曲线长端 |
| 3M T-Bill | `TB3MS` | 1934-01-01 | 月 | 曲线短端 / 现金利率 |
| 3M T-Bill(日) | `DTB3` | 1954-01-04 | 日 | 日频短端 |
| 联邦基金利率 | `FEDFUNDS` | 1954-07-01 | 月 | 政策利率 |
| CPI | `CPIAUCSL` | 1947-01-01 | 月 | 通胀压力 |
| 工业生产 | `INDPRO` | 1919-01-01 | 月 | 衰退/经济压力 |
| 失业率 | `UNRATE` | 1948-01-01 | 月 | 宏观压力 |
| M1/M2 | `M1SL` / `M2SL` | 1959-01-01 | 月 | 流动性/货币增速 |
| Aaa 企业债 | `AAA` | 1919-01-01 | 月 | 信用高等级 |
| Baa 企业债 | `BAA` | 1919-01-01 | 月 | 信用低等级 |
| WTI（月） | `OILPRICE` | 1946-01-01 | 月 | 1970s 油价冲击（已 discontinued 但历史可用） |

推荐 1970s 回测窗口：

1. `1968-01-01 ~ 1970-12-31`：Nifty Fifty / 通胀升温 / 1970 衰退
2. `1973-01-01 ~ 1975-12-31`：第一次石油危机 + 股债双杀
3. `1978-01-01 ~ 1982-12-31`：第二次石油冲击 + Volcker 加息

### 1929（只能做月频/代理，不要假装日频完整）

1929 没有 VIX、SOFR、现代信用 OAS、日频 SPX/FRED 数据。可行方案是**月频代理回测**：

| 代理 | 数据源 | 起始 | 频率 | 说明 |
|---|---|---:|---|---|
| 股票价格 / EPS / 股息 / CPI / CAPE | Robert Shiller / DataHub `s-and-p-500` CSV | 1871-01 | 月 | 可做估值与股价 drawdown |
| Aaa / Baa 企业债 | FRED `AAA` / `BAA` | 1919-01 | 月 | 可算 Baa-Aaa 信用利差 |
| 工业生产 | FRED `INDPRO` | 1919-01 | 月 | 可看经济下行 |
| 3M T-Bill | FRED `TB3MS` | 1934-01 | 月 | **不能覆盖 1929**,只能覆盖 1934 后 |
| DJIA 日频 | MeasuringWorth DJA 页面 | 1885/1896+ | 日 | 页面可取,但无稳定 CSV/API；需用户人工导出或授权使用 |

DataHub/Shiller CSV 已实测可读：

```text
https://datahub.io/core/s-and-p-500/r/data.csv
https://raw.githubusercontent.com/datasets/s-and-p-500/master/data/data.csv
```

CSV columns：

```text
Date,SP500,Dividend,Earnings,Consumer Price Index,Long Interest Rate,Real Price,Real Dividend,Real Earnings,PE10
```

推荐 1929 回测窗口：

1. `1928-01 ~ 1933-12`（月频）：股价/CAPE/BAA-AAA/INDPRO
2. `1929-09 ~ 1932-07`（若用户人工取 DJIA 日频）：崩盘到大萧条低点

## 不能做 / 不应硬做的事

- 不要把 VIX/VVIX/SKEW 强行外推到 1929/1970s。
- 不要用现代 OAS 系列硬套 1929/1970s；HY OAS、IG OAS 历史太短。
- 不要假装 1929 能跑当前 22 条指标的完整综合分；那会产生伪精确。
- 不要引入付费源或 akshare 来解决美股老历史。

## 建议实现路线

### iter 64 候选：月频 old-history 回测引擎

新增 `src/backtest/old_history.py`：

- `OLD_HISTORY_INDICATORS`（只含老历史可用代理）
  - `shiller_sp500_drawdown`
  - `shiller_cape`
  - `baa_aaa_spread = BAA - AAA`
  - `industrial_production_yoy`
  - `cpi_yoy`
  - `oil_yoy`（1970s only）
- 单独输出月频 CSV，不和现有日频 backtest 混在一起。

### iter 65 候选：1970s 三窗口实跑

用 FRED 直接跑：

- 1968-1970
- 1973-1975
- 1978-1982

目标不是给出交易信号，而是验证：系统在通胀/油价/利率冲击下是否会升温。

### iter 66 候选：1929 月频代理回测

使用 DataHub/Shiller CSV + FRED AAA/BAA/INDPRO：

- 1928-1933 月频
- 指标不全时输出 missing pattern，不做日频假象。

## 需要用户人工取 / 决策的项目

1. **DJIA 日频 1929 数据**
   - 来源：MeasuringWorth DJA 页面
   - 页面说明可取 1885/1896 至今 DJIA 日收盘，非商业教育用途可用。
   - 但无稳定 CSV/API；用户若想日频 1929，需要人工导出或确认是否允许我写爬取表单。

2. **是否接受月频回测**
   - 1929/1970s 高质量免费数据多数是月频。
   - 若用户坚持日频，1929 基本需要人工/第三方数据。

3. **是否把 old-history 纳入综合温度计同一分数**
   - 建议不要。old-history 用代理指标和月频，应输出单独 old-risk score，避免和现代 22 条日频指标混用。

## 本轮客观评价

这个调研有意义，因为它避免了“为了回测而伪造精确度”。
1970s 可以做，1929 只能做月频代理；这是系统必须诚实面对的数据边界。
