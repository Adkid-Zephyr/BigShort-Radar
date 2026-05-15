# 上一轮总结

迭代 27（2026-05-15）：LLM 接入完成，每日风险简报上线 dashboard 顶部。

本轮做了：
- DECISIONS.md 追加 ADR：服务商=阿里百炼 Coding Plan（用户授权），OpenAI 协议，依赖只用 requests（白名单内）
- src/utils/config.py：Settings 加 llm_api_key/llm_base_url/llm_model 三字段（默认值，缺则降级）
- src/fetch/llm_client.py：chat(messages, settings) 函数，requests 调 /v1/chat/completions
- tests/test_llm_client.py：7 用例（成功/无 key/无 base/HTTP 错/网络异常/解析错/model 注入）
- src/compute/briefing.py：build_snapshot + run_and_store + briefings 表 schema/CRUD
- tests/test_briefing.py：8 用例（snapshot/CRUD/upsert/run_and_store）
- scripts/daily_fetch.py：跑完后自动调一次 LLM 简报，失败优雅降级
- src/web/app.py：index() 加 latest_briefing 渲染
- templates/index.html：顶部加暗色简报卡片（含日期 + 模型名）
- .env.example：加 DASHSCOPE_API_KEY/BASE_URL/MODEL 字段
- PLAN.md：P3 加 LLM 接入 [x]、加 P3.5 日本与跨市场维度

测试情况：
- pytest 共 148 通过 / 0 失败 / 0 skip（+15）
- 真打验证：百炼 qwen3-coder-plus 调用成功，生成 307 字简报已入库
- dashboard localhost:5050 顶部渲染简报正常

关键发现：
- qwen-max 在 Coding Plan endpoint 不支持（400 invalid_parameter_error），需用 qwen3-coder-plus
- Coding Plan 走 OpenAI 协议 /v1/chat/completions，标准 Bearer auth

git：iter 26 收尾 34c9892 → iter 27 待 commit。

下一步候选（按用户"按计划做下去"+ 自治路线推荐）：
- iter 28：日本与跨市场维度 — 加 USDJPY / DXY / 日本 10Y / BoJ 资产规模 4 条指标，凑成"日本"分组
- iter 29：综合温度计 — 七条指标加权 → 单一 0-100 风险分（让 dashboard 从 7 块表变 1 支温度计）
- iter 30：/chat 对话接口 — 用户对当前数据追问 LLM
- iter 31：launchd 自动化 — 每天美东 16:30 自动跑 daily_fetch + 简报

按用户授权"一直做下去"，下一句"继续"将按 28→29→30→31 顺序连跑。
