# ARCHITECTURE

## 一句话

本地运行的 Python 应用：定时脚本拉数据 → 写 SQLite → Flask Dashboard 读 SQLite → 浏览器看。

## 分层

```
                  ┌───────────────────────┐
                  │   Browser (localhost) │
                  └──────────▲────────────┘
                             │ HTTP
                  ┌──────────┴────────────┐
                  │   Flask  src/web/     │  ← 渲染层（薄）
                  └──────────▲────────────┘
                             │ 函数调用
                  ┌──────────┴────────────┐
                  │   src/compute/        │  ← 指标计算 + 阈值
                  └──────────▲────────────┘
                             │ 读写
                  ┌──────────┴────────────┐
                  │   src/store/  SQLite  │  ← 唯一真相源
                  └──────────▲────────────┘
                             │ 写入
                  ┌──────────┴────────────┐
                  │   src/fetch/          │  ← 外部数据源封装
                  └──────────▲────────────┘
                             │ 网络
                  ┌──────────┴────────────┐
                  │ FRED / yfinance / ... │
                  └───────────────────────┘
```

## 模块边界

- **src/fetch/**：只负责"从外部把数据拿回来"，纯函数式，返回 DataFrame 或 dict。每个数据源一个客户端文件
- **src/store/**：SQLite 封装。其他模块只通过这里读写库，不允许直连 sqlite3
- **src/compute/**：指标定义 + 阈值分类。每个指标一个文件 `indicators/<name>.py`，包含 `fetch()` 调 fetch 层、`compute()` 算衍生值、`classify()` 出三档
- **src/web/**：Flask 路由 + 模板。路由只做"调 store 拿数据 → 渲染"，不算指标
- **src/utils/**：logger / config / 时间转换等公共工具
- **scripts/**：可执行脚本（daily_fetch.py / backup.py 等）
- **tests/**：与 src 镜像结构

## 数据库 schema（v1，改动需 ADR）

```sql
CREATE TABLE indicators (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,           -- yield_curve_10y2y
  date TEXT NOT NULL,           -- ISO YYYY-MM-DD（指标本身的日期，不是入库时间）
  value REAL NOT NULL,
  source TEXT NOT NULL,         -- FRED:T10Y2Y / YF:^VIX
  ingested_at TEXT NOT NULL,    -- UTC ISO timestamp
  UNIQUE(name, date)
);
CREATE INDEX idx_name_date ON indicators(name, date);
```

后续可能新增表（events / positions / notes），新增需 DECISIONS.md 记录。

## 配置

- 所有运行时配置走 `.env`
- 常量（端口、DB 路径、阈值默认值）走 `src/utils/config.py`
- 阈值定义放在 `INDICATORS.md` 的对应章节，代码里的阈值变更必须同步该文件

## 扩展约定

加一个新指标 = 加一个文件 `src/compute/indicators/<name>.py` + 一个测试 + INDICATORS.md 一段。不需要改任何注册表（Dashboard 通过约定扫描）。

## 测试

- 单元测试覆盖 store / compute / classify
- fetch 层测试用 mock，不打真实网络
- 端到端测试：跑一次 daily_fetch（mock 数据源）→ 启动 Flask → requests.get 拿首页 → 断言指标存在

## 不做的事（明确边界）

- 不做实时分钟级行情（那是经纪商 App 的事）
- 不做交易执行（信号系统不是下单系统）
- 不做账户聚合（隐私敏感）
- 不引入 ORM、不引入消息队列、不引入容器（MVP 阶段简化优先）
