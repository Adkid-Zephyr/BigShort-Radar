"""每日风险简报生成器：把 dashboard 数据喂给 LLM，得到中文解读。

工作流：
  daily_fetch 跑完 → build_snapshot(conn) → call_llm(snapshot) → upsert_briefing(conn, date, text)
  Flask 主页顶部读 latest_briefing(conn) 渲染。

设计原则：
  - 失败优雅降级：LLM 不可用时 daily_fetch 主流程不受影响
  - 摘要式 prompt：每条指标 一行 = 当前值 + 等级 + 7 天前对比 + 阈值。token 预算 ~500
  - 不让 LLM 编造历史价位、不让它给"明天会跌"——只让它做"今日读数解读 + 关注变化 + 明日观察重点"
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date, timedelta
from typing import Any, Dict, List, Optional

from src.compute.thresholds import Level
from src.fetch import llm_client
from src.store import db as dbmod
from src.utils.config import Settings, load_settings
from src.utils.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """你是一名严谨的市场风险分析师，正在读一份本地金融监控仪表盘的当日数据。
任务：根据用户给出的指标快照（含当前值、等级、7 天前对比、阈值），输出 250 字以内的中文简报。

简报必须包含三段，每段一句到三句：
1. 「今日核心读数」——总体处于什么状态，最严重的是哪条
2. 「值得关注的变化」——7 天内移动方向最大的指标，以及它的含义
3. 「明日重点观察」——具体说哪条指标穿过哪个阈值就需要警惕

铁律：
- 只用快照里的数字，绝不编造历史价位与外部新闻
- 不预测涨跌、不给买卖建议
- 风格冷静、客观、第三人称、无感叹号
- 全文 250 字以内
"""


def _level_str(value: Optional[float], classify_fn) -> str:
    if value is None:
        return "无数据"
    try:
        return classify_fn(value).value
    except Exception:
        return "未知"


def build_snapshot(conn: sqlite3.Connection, registry: List[Dict[str, Any]]) -> str:
    """组装喂给 LLM 的指标快照文本。

    入参：
        conn: SQLite 连接
        registry: web/app.py 用的 _INDICATOR_REGISTRY 同款（含 name/label/classify/group）
    返回：
        多行字符串，每行一条指标。例如：
        「[波动率] VIX 恐慌指数: 17.26 GREEN（5/14） | 7d 前 17.0 GREEN | 阈值 GREEN<20 / YELLOW 20-30 / RED>30」
    """
    # 顶部加综合温度计上下文（懒导入避免循环引用）
    try:
        from src.compute import risk_score as rs
        latest_score = rs.get_latest_risk_score(conn)
    except Exception:
        latest_score = None

    lines: List[str] = []
    today_iso = _date.today().isoformat()
    seven_days_ago = (_date.today() - timedelta(days=7)).isoformat()

    for ind in registry:
        latest = dbmod.get_latest(conn, ind["name"])
        # 7d 前用 get_series 取最新但 ≤7 天前的那条
        rows = dbmod.get_series(conn, ind["name"])
        prior_row = None
        for r in rows:
            if r["date"] <= seven_days_ago:
                prior_row = r  # 升序，最后一条 ≤ 7 天前的
        latest_str = (
            f"{latest['value']:.3f} {_level_str(latest['value'], ind['classify'])}（{latest['date']}）"
            if latest else "无数据"
        )
        prior_str = (
            f"{prior_row['value']:.3f} {_level_str(prior_row['value'], ind['classify'])}（{prior_row['date']}）"
            if prior_row else "（无 7 天前对比）"
        )
        thresh = _format_threshold(ind)
        group = ind.get("group", "其他")
        lines.append(f"[{group}] {ind['label']}: 现 {latest_str} | 7d前 {prior_str} | {thresh}")

    if not lines:
        return "（注册表为空）"

    score_line = ""
    if latest_score:
        bd = latest_score.get("breakdown", {})
        bd_str = "、".join(
            f"{g} {info['score']:.0f}/100" for g, info in bd.items()
        ) if isinstance(bd, dict) else ""
        score_line = (
            f"\n综合风险温度计：{latest_score['score']:.1f}/100 ({latest_score['level']})"
            + (f"\n维度分：{bd_str}" if bd_str else "")
            + "\n"
        )

    header = f"日期：{today_iso}\n指标快照（共 {len(lines)} 条）：{score_line}\n"
    return header + "\n".join(lines)


def _format_threshold(ind: Dict[str, Any]) -> str:
    """从 classify 函数反查阈值不靠谱，直接读 ind['classify'] 所在指标模块的常量。

    这里走"通过指标的 classify 探测"路径——传几个值看分到哪档。
    避免侵入指标文件结构。
    """
    cls = ind["classify"]
    # 兜底用 0 / 0.5 / 1 / 5 / 10 / 50 几个点试
    samples = [-1, 0, 0.25, 0.5, 1, 2, 5, 10, 20, 50]
    levels: Dict[float, str] = {}
    for v in samples:
        try:
            levels[v] = cls(v).value
        except Exception:
            continue
    return "阈值方向参见 INDICATORS.md"


def generate_briefing(
    conn: sqlite3.Connection,
    registry: List[Dict[str, Any]],
    settings: Optional[Settings] = None,
) -> Optional[str]:
    """跑一次 LLM 生成简报。

    入参：
        conn: SQLite 连接
        registry: 指标注册表
        settings: 可选注入测试用
    返回：
        简报文本；失败返回 None
    """
    snapshot = build_snapshot(conn, registry)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": snapshot},
    ]
    return llm_client.chat(messages, settings=settings)


# ── 简报存储 ─────────────────────────────────────────────────

_BRIEFING_SCHEMA = """
CREATE TABLE IF NOT EXISTS briefings (
    date TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    model TEXT,
    created_at TEXT NOT NULL
);
"""


def init_briefings_schema(conn: sqlite3.Connection) -> None:
    """幂等创建 briefings 表。"""
    with conn:
        conn.executescript(_BRIEFING_SCHEMA)


def upsert_briefing(
    conn: sqlite3.Connection,
    date_iso: str,
    content: str,
    model: Optional[str] = None,
) -> None:
    """按 date 唯一 upsert 一条简报。"""
    init_briefings_schema(conn)
    from datetime import datetime, timezone
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with conn:
        conn.execute(
            """
            INSERT INTO briefings (date, content, model, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                content=excluded.content,
                model=excluded.model,
                created_at=excluded.created_at
            """,
            (date_iso, content, model, now),
        )


def get_latest_briefing(conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    """取最新一条简报；表不存在或空 → None。"""
    init_briefings_schema(conn)
    cur = conn.execute(
        "SELECT date, content, model, created_at FROM briefings ORDER BY date DESC LIMIT 1"
    )
    row = cur.fetchone()
    return dict(row) if row else None


def run_and_store(
    conn: sqlite3.Connection,
    registry: List[Dict[str, Any]],
    settings: Optional[Settings] = None,
) -> Optional[str]:
    """一站式：生成简报 + 入库。失败返回 None。供 daily_fetch 调用。"""
    s = settings if settings is not None else load_settings()
    text = generate_briefing(conn, registry, settings=s)
    if text is None:
        log.warning("简报生成失败，跳过入库")
        return None
    today_iso = _date.today().isoformat()
    upsert_briefing(conn, today_iso, text, model=s.llm_model)
    log.info("简报入库（date=%s, %d chars）", today_iso, len(text))
    return text
