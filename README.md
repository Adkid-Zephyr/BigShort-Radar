# Finance Radar

本地金融风险监控系统：每日自动采集宏观与市场指标，按维度加权算综合温度计，
LLM 生成中文简报与对话式追问，跨设备 / 跨 AI 接力开发。

> **第一原则**：所有工作为 [`THESIS.md`](./THESIS.md) 服务——投资论点 / 危机传导链候选剧本 / 反共识结构性观察。任何修改都要先回头确认对应论点章节。

> 定位：**风险温度计 + 仓位调节器 + 认知输出原料库**。
> 不预测崩盘，不给买卖时点。目标是让用户**在风险持续累积期活得够久 + 当尾部事件真正发生时不缺席**。

## 当前能力

- **10 条核心指标**，分 5 维度：
  - 波动率：VIX、VIX 期限结构（VIX/VIX3M）
  - 曲线：10Y-2Y、10Y-3M
  - 信用：HY OAS、IG OAS
  - 流动性：SOFR-IORB
  - 跨市场：USDJPY、DXY、日本 10Y
- **综合风险温度计** 0-100 分，五维加权（曲线 25 / 信用 25 / 跨市场 20 / 流动性 15 / 波动率 15）
- **LLM 风险简报**：每日自动跑完 fetcher 后，调阿里百炼 qwen3-coder-plus 出 250 字中文简报
- **chatbot 对话**：dashboard 浮窗，基于当前真实数据追问 LLM
- **launchd 自动化**：北京时间 05:30 每日自动跑（≈ 美东收盘后半小时）
- **测试覆盖**：167 用例 / 0 失败 / 0 skip

## 一分钟启动

```bash
cd /Users/lau/finance-radar

# 1. 建虚拟环境
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. 配置 .env
cp .env.example .env
# 编辑 .env，填入：
#   FRED_API_KEY=你的key（必需，注册见下方）
#   DASHSCOPE_API_KEY=你的百炼key（可选，缺失时 LLM 功能降级）

# 3. 拉数据（首次几秒钟）
python -m scripts.daily_fetch

# 4. 起 dashboard
python -m src.web.app
# 浏览器打开 http://localhost:5050
```

跑测试：

```bash
.venv/bin/pytest -q
```

## 启用每日自动运行（macOS launchd）

```bash
bash scripts/install_launchd.sh install     # 装 + 启用
bash scripts/install_launchd.sh status      # 看运行状态
bash scripts/install_launchd.sh runonce     # 立即手动触发一次
bash scripts/install_launchd.sh uninstall   # 卸载
```

触发时间：每天 05:30（Asia/Shanghai），≈ 美东收盘后半小时。
日志写到 `logs/launchd.out` 和 `logs/launchd.err`。

## API Key 申请

### FRED（必需，免费）

1. 打开 <https://fred.stlouisfed.org/>
2. 右上角 **My Account** → **Register** → 邮箱验证
3. 进 <https://fred.stlouisfed.org/docs/api/api_key.html> → **Request API Key**
   填"个人金融研究"用途，秒批
4. 32 位字符串写到 `.env`：`FRED_API_KEY=...`

### 阿里百炼（可选，付费）

LLM 简报与 chatbot 用。缺失时这两个功能自动降级（dashboard 仍可看，每日数据照常入库）。

1. <https://bailian.console.aliyun.com/> 开通 Coding Plan
2. 拿 API Key（`sk-sp-` 开头），写到 `.env`：
   ```
   DASHSCOPE_API_KEY=sk-sp-...
   DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
   DASHSCOPE_MODEL=qwen3-coder-plus
   ```

## 项目文件导览

| 文件 | 用途 |
| --- | --- |
| `THESIS.md` | **第一原则** — 投资论点 / 危机传导链 / 反共识观察 / 缺失内容优先级 |
| `PROMPT.md` | Vibe coding 工作宪法，新会话直接喂这个 |
| `PLAN.md` | 任务列表，开发循环吃这个，做完打勾 |
| `INDICATORS.md` | 指标说明书 + 阈值依据（翻译卡用户手写） |
| `ARCHITECTURE.md` | 架构与目录约定 |
| `DECISIONS.md` | ADR 风格的决策记录 |
| `HANDOFF.md` | 接力手册：新 agent 看完这个能立刻续上 |
| `.ralph/last-summary.md` | 上一轮做了什么（跨轮记忆） |
| `.ralph/iteration.txt` | 当前迭代号 |
| `.env.example` | 环境变量样板，复制为 `.env` 后填值 |

## 接力开发约定

任何新 agent / 新设备打开仓库后：

1. 先读 `HANDOFF.md`（30 秒上下文）
2. 跑 `.venv/bin/pytest -q` 确认基线绿
3. 看 `.ralph/last-summary.md` 知道上一轮做到哪
4. 找 `PLAN.md` 顶上的第一个 `[ ]`，按 `PROMPT.md` 工作循环跑一轮
5. 收尾必做：测试通过 + 打勾 + commit + 更新 last-summary + iteration+1

详见 `HANDOFF.md` §6 留痕规范。

## 维度与阈值（一览）

| 指标 | 来源 | 方向 | GREEN | YELLOW | RED |
| --- | --- | --- | --- | --- | --- |
| VIX | YF ^VIX | up | < 20 | 20–30 | > 30 |
| VIX 期限结构 | YF ^VIX/^VIX3M | up | < 0.95 | 0.95–1.0 | > 1.0 |
| 10Y-2Y | FRED T10Y2Y | down | > 0.5 | 0–0.5 | < 0 |
| 10Y-3M | FRED T10Y3M | down | > 0.5 | 0–0.5 | < 0 |
| HY OAS | FRED BAMLH0A0HYM2 | up | < 4 | 4–8 | > 8 |
| IG OAS | FRED BAMLC0A0CM | up | < 1.5 | 1.5–3 | > 3 |
| SOFR-IORB | FRED SOFR/IORB | up | < 5 bp | 5–15 bp | > 15 bp |
| USDJPY | FRED DEXJPUS | up | < 145 | 145–160 | > 160 |
| DXY 广义 | FRED DTWEXBGS | up | < 110 | 110–125 | > 125 |
| 日本 10Y | FRED IRLTLT01JPM156N | up | < 1.0 | 1.0–2.0 | > 2.0 |

阈值依据见 `INDICATORS.md` 与 `DECISIONS.md`。

## 综合温度计算法

```
每条指标按 Level 转分：GREEN=0 / YELLOW=50 / RED=100
同 group 内取算术平均 → 维度分
维度分 × 维度权重 → 总分
```

权重：曲线 25 / 信用 25 / 跨市场 20 / 流动性 15 / 波动率 15（合 100）

总分阈值：< 25 GREEN / 25–65 YELLOW / ≥ 65 RED

## 不做的事（明确边界）

- 不做实时分钟级行情
- 不做交易执行（信号系统不是下单系统）
- 不做账户聚合
- 不引入 ORM、消息队列、容器（MVP 简化优先）

## License

私有项目，未发布。
