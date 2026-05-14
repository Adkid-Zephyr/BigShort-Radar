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
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 填 FRED_API_KEY
python -m src.web.app  # http://localhost:5050
```

## 每日定时

`scripts/daily_fetch.sh` + macOS launchd（部署在 P2 阶段）。
