# Finance Radar

本地金融风险监控系统。每日自动采集宏观/市场指标，计算风险分级，本地 Web Dashboard 显示。

定位：**风险温度计 + 仓位调节器 + 认知输出原料库**。
不是做空信号机。指标会告诉你"风险在累积"，不会告诉你"明天空"。

## 核心文件

- `PROMPT.md` — vibe coding 主 prompt，新对话直接粘进去
- `PLAN.md` — 任务列表，开发循环吃这个，每完成一项打勾
- `INDICATORS.md` — 指标说明书 + 翻译卡（用户手写为主，模型只能按既定规则补充）
- `ARCHITECTURE.md` — 架构与目录约定
- `DECISIONS.md` — 重要技术决策记录（ADR 风格）
- `BLOCKED.md` — 遇到必须人工介入时由模型创建，存在则中断循环
- `.ralph/last-summary.md` — 上一轮做了什么（跨轮记忆）
- `.ralph/iteration.txt` — 当前迭代计数
- `.env.example` — 环境变量样板（FRED key 等）

## 开发模式

vibe coding：开新对话粘 PROMPT.md，让它读 PLAN.md 找下一个 [ ]，做完打勾、写 last-summary、commit，回复"继续"就进入下一轮。

## 启动

```bash
cd /Users/lau/finance-radar

# 1. 建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 2. 装依赖
pip install -r requirements.txt

# 3. 准备配置（FRED_API_KEY 暂时可以留空，VIX 不需要）
cp .env.example .env
# 编辑 .env，填好 FRED_API_KEY=（可选）和 TZ=Asia/Shanghai

# 4. 拉一遍数据入库（首次会从 2020-01-01 拉到今天，几秒钟）
python -m scripts.daily_fetch

# 5. 起 Web Dashboard
python -m src.web.app
# 浏览器打开 http://localhost:5050 → 看到 VIX 当前值与颜色
```

跑测试：

```bash
.venv/bin/pytest -q
```

## 已实现指标

| 指标 | 来源 | 阈值（默认） |
| --- | --- | --- |
| VIX 恐慌指数 | yfinance ^VIX | GREEN ≤ 20 / YELLOW 20–30 / RED > 30 |

后续指标见 `PLAN.md` P1。FRED 系列（10Y-2Y、HY OAS、IG OAS 等）需要 API key，注册指引见下方。

## FRED API Key 注册指引

1. 打开 https://fred.stlouisfed.org/
2. 右上 "My Account" → "Register" → 用邮箱注册并验证
3. 登录后进 https://fred.stlouisfed.org/docs/api/api_key.html → "Request API Key" → 填一句"个人金融研究"用途即可，秒批
4. 拿到的 32 位字符串写进 `.env`：`FRED_API_KEY=你的key`
5. 跑 `python -m scripts.daily_fetch`，FRED 系列就会自动生效

## 每日定时

`scripts/daily_fetch.py` + macOS launchd（部署在 P4 阶段）。
