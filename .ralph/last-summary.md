# 上一轮总结

迭代 12–17（2026-05-15）：用户拍板首条指标走 VIX → 一口气把 P0 跑完，里程碑达成。

本轮做了（共 6 轮）：
- iter 12：决策落地——P0 首条指标走 VIX(yfinance)；DECISIONS.md 记录；PLAN 重排（VIX 上提到 P0、P1 删原 VIX 重复项）
- iter 13：src/compute/indicators/vix.py（fetch+classify+upsert，NaN/Inf 跳过）+ test_vix.py（9 通过）。阈值默认值代码常量：GREEN ≤20 / YELLOW 20-30 / RED >30
- iter 14：src/web/app.py（create_app 工厂、INDICATOR_REGISTRY、/ 与 /healthz）+ templates/index.html（暗色极简表格）+ test_web.py（4 通过）
- iter 15：scripts/daily_fetch.py（argparse + Fetcher 注册表 + 单 fetcher 失败隔离）+ test_daily_fetch.py（5 通过）
- iter 16：README 跑通指南（venv → pip → .env → daily_fetch → flask）+ 已实现指标表 + FRED key 注册指引段
- iter 17：里程碑验证——venv 加装 yfinance + flask；真跑 daily_fetch 拉到 342 条 VIX；起 Flask；curl / 渲染出 VIX 17.26 GREEN（2026-05-14 收盘）

测试情况：
- pytest 共 60 通过 / 0 失败 / 0 skip
- venv 累计装：pytest、pandas、flask、yfinance（含连带依赖如 numpy/jinja2/curl_cffi 等）。requirements.txt 白名单内的还差 fredapi、plotly、python-dotenv、requests，等用到时再装

P0 状态：**全部 [x]**。里程碑已达成（localhost:5050 看到 VIX GREEN）。

可以走 P1 了。下一项 PLAN 顶上的未阻塞 [ ]：
- 顶部 P0 里那个 fred_client.py 还是 ⏸ 待 API key
- P1 第一项 10Y-3M（FRED）⏸；HY OAS、IG OAS 也 ⏸
- 第一个未阻塞的是 P1 中的 **VIX 期限结构（VIX vs VIX3M / VIX6M）** — 但意义不大，且原 PLAN 中"VIX"那行我已删（合到 P0），剩下"VIX 期限结构"独立成项
- 再往下未阻塞的：Shiller PE（CSV）、Buffett Indicator（Wilshire/GDP）、Dashboard 分组

建议下一轮做 **Shiller PE**（公开 CSV，估值维度，与 VIX 互补），让 dashboard 上多一条不同维度的指标。

或者用户给 FRED key 后立即铺 fred_client.py + 4 个 FRED 指标，一波铺平 P1 大半。
