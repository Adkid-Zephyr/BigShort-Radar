# iter 57 收尾必做:全局复盘 + 期权交易者视角缺口分析

用户 2026-05-17 提出的额外要求(iter 57 完成后必须交付):

## 1. 自我审视

对当前 19 条指标 + 7 维度 + 5 个崩盘剧本 + 阈值算法,逐条诚实评估:
- **真正有意义**(对监控系统目标和未来辅助期权交易都有用)
- **可能没意义**(看起来专业但对实战决策没助力,或重复指标)
- **当前空的/未显示**的指标真实原因(yahoo 限速 / FRED 历史不够 / 派生未入 cache 等)

## 2. 用户实际交易标的

辅助交易标的列表:
- 沪深 300 期权(50 ETF / 300 ETF / 中金所 IO)
- 上证 50 期权
- 纳指期权(QQQ / NDX)
- 美股七姐妹个股期权(AAPL / MSFT / GOOGL / AMZN / META / NVDA / TSLA)

围绕这些标的,期权交易者真正盯的数据(当前系统**完全没追踪**):

### 波动率结构(期权核心)
- IV (隐含波动率)历史百分位 — 当前只有 VIX,没追个股 / 个股 ETF
- IV Skew(看跌-看涨偏度)— THESIS §4.2 提到但没数据
- IV Term Structure(短中长 IV 期限结构反转)
- 0DTE / 周期权占比 — 反身性核心,当前完全没

### 仓位 / 资金流(Dealer Positioning)
- Put/Call Ratio(总市场 / 个股)
- Gamma Exposure(GEX)— 做市商净 gamma 暴露(决定市场是 mean-revert 还是 trend)
- Dealer Net Positioning(SPX 期权)
- 大单异动(Unusual Options Activity)
- DIX(Dark Pool 资金流向)

### 中国市场(几乎完全空白)
- 50 ETF 期权 IV / 月度 / 行权偏度
- 300 ETF 期权同上
- 沪深 300 IV 指数(中金所类似 VIX 的 iVIX)— 当前没有
- 北向 / 南向资金日数据
- 融资余额 / 融券余额

### 美股微观结构
- VIX9D / VIX1Y(超短超长波动率)— 当前只 VIX + VIX3M
- SPX 期限结构 contango / backwardation 标志
- VVIX / SKEW 已有但 yahoo 限速 backfill 漏拉

### 宏观 / 联动(部分已有,但需要更直接给期权信号)
- DXY 对七姐妹 EPS 影响传导(当前 DXY 已有)
- 联储票委鹰鸽分歧度
- 美债期限溢价(ACM / Kim-Wright)

## 3. 数据源调研(用户需协助/确认)

哪些我能自己接(免费 API 内):
- FRED:VIXCLS 已接;FRED 上还有 VXVCLS(VIX3M)/ VXOCLS(VXO)等
- Yahoo Finance 个股 IV30 / put_call_ratio 部分有但限速严重
- CBOE 直接 CSV(VVIX / SKEW / Put-Call Ratio)— 之前 iter 45 提过

哪些需要用户找(需要付费 / 注册账号):
- ORATS / IVolatility / Tiingo Options(个股 IV historical)
- 50ETF / 300ETF 期权数据 — 中金所 / 上交所有日报但需要爬虫
- GEX / Dealer Positioning — SqueezeMetrics / SpotGamma(付费)
- 北向南向 — 港交所 / 同花顺接口

## 4. 交付形式

iter 57 完成 commit/push 后,在最后单独输出一份 markdown 给用户:
- 标题:`iter 57 复盘 + 期权交易者视角缺口分析`
- 三段:有意义的 / 没意义的(或重复) / 期权视角缺什么 → 给出清单让用户挑下一轮做什么
- 不直接进 PLAN.md,等用户拍板后再进

## 5. 不要忘

- 当前 dashboard "暂无数据"的那几条:vvix / skew / vix(主流程,yahoo 限速)— 这些用 cache_db 里 vix_fred 等替代是否靠谱要回答
- 主流程 daily_fetch 跑一次确认到底哪几条真没数据
