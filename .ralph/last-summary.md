# 上一轮总结

迭代 37（2026-05-17）：README 文风重写 + 第二阶段 14 轮路线图。

本轮做了：

- **README.md 全量重写**（240 行 → 246 行密度更高）：
  - 调研 6 个金融/量化开源项目（AKShare/Zipline/Qlib/QSTrader/yfinance/FinanceDatabase）的 README 文风
  - 对照规则：去 emoji、去营销词（"赋能/极致/强大/优雅/为人类"）、一句话简介改事实陈述（不用"X is a Y" 模板）、章节扁平化、工程师口吻 70%+价值阐述 30%
  - 验证：grep 0 emoji / 0 营销词
  - 保留：徽章、阈值表、Quickstart、API key、文件导览
  - 加：Roadmap 段写入 14 轮路线图
- **PLAN.md** 加"第二阶段路线图（iter 38–50）"段：
  - iter 37 README ✅
  - iter 38 历史 cache DB + akshare ADR
  - iter 39 Sparkline 90 天
  - iter 40 同环比对比
  - iter 41 5 年回填 + Z-score
  - iter 42 加速度
  - iter 43 政策 3 条 (WALCL/ON RRP/TGA)
  - iter 44 波动率 2 条 (VVIX/SKEW)
  - iter 45 FRA-OIS + 中国骨架
  - iter 46 中国 6 条
  - iter 47 异常事件流
  - iter 48 组合信号 + 5 剧本检测器
  - iter 49 热力图 + 时间线
  - iter 50 政策对冲对比 + 阈值校准
  - 暂搁：USD basis swap / 国债基差杠杆 / TIC / 日 30Y（无源或 HTML 爬虫）
  - 历史回测后置到 iter 51+
- **DECISIONS.md** 加 iter 37 ADR：文风规则 + 路线图决策（26 条 / 7 维度 / 异常监测分层）+ akshare 引入需 ADR 评估 + 历史回测后置原因

测试：pytest 197 通过 / 0 失败 / 0 skip（纯文档变更）。

git：iter 36 a4f7022 → iter 37 待 commit。

## 下一轮（iter 38）

历史数据基础设施：

1. **akshare 加白名单**：先评估对"测试不打真实网络"的影响，写专门 ADR 到 DECISIONS.md，然后加 requirements.txt
2. 新建 `data/historical_cache.sqlite`（独立 schema）
3. 新建 `src/store/history_db.py`：cache DB 的 upsert/get_series 操作
4. 新建 `src/fetch/history_fetcher.py`：通用历史拉取（FRED `start=` / YF `period="5y"` / akshare 各 series wrapper）
5. 新建 `scripts/backfill_history.py`：一次性回填脚本
6. mock 各 client 写 `tests/test_history_*`

iter 38 不展示新指标，只搭基础设施。iter 39 起 Sparkline 才会用上这些数据。

下一句"继续"将进 iter 38。
