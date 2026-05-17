"""综合风险温度计：把所有指标加权成一个 0-100 风险分。

设计：
  1. 每个指标按当前 Level 转分（GREEN=0 / YELLOW=50 / RED=100；缺数据 → 跳过）
  2. 同一 group 取算术平均 = 维度分
  3. 维度按 _GROUP_WEIGHTS 加权 = 总分（已实现的维度权重总和归一化）
  4. 总分 0-100，分档：< 25 GREEN / 25-65 YELLOW / > 65 RED

权重默认值（DECISIONS.md 2026-05-15 ADR）：
  曲线   25%   收益率曲线倒挂是衰退最强先行信号
  信用   25%   信用利差是危机定价最快反应
  流动性 15%   SOFR-IORB / FRA-OIS 是危机引爆器
  波动率 15%   VIX 是市场恐慌度但偶尔失灵
  跨市场 20%   日元 carry / 强美元 / 日银货币是 2025-26 主剧本

权重之和必须 100；改权重需走 ADR。

写库 schema：risk_score(date, score, level, breakdown_json, created_at)
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, date as _date
from typing import Any, Dict, List, Optional

from src.compute.thresholds import Level
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

# Level → 分数（线性）
_LEVEL_SCORE = {Level.GREEN: 0.0, Level.YELLOW: 50.0, Level.RED: 100.0}

# 维度权重（DECISIONS.md 2026-05-15/2026-05-17 ADR；iter 46 加入"中国"维度再平衡）
_GROUP_WEIGHTS: Dict[str, float] = {
    "曲线": 20.0,
    "信用": 20.0,
    "流动性": 14.0,    # 含 SOFR-IORB + FRA-OIS
    "波动率": 12.0,    # 含 VIX/VIX 期限/VVIX/SKEW
    "跨市场": 14.0,    # 美元/日元/日 10Y
    "政策": 10.0,      # WALCL/ON RRP/TGA
    "中国": 10.0,      # 外储/USDCNY/CNY 10Y
}

# 总分阈值
SCORE_GREEN_MAX = 25.0
SCORE_RED_MIN = 65.0


def _classify_total(score: float) -> str:
    if score < SCORE_GREEN_MAX:
        return "GREEN"
    if score >= SCORE_RED_MIN:
        return "RED"
    return "YELLOW"


def compute_score(
    conn: sqlite3.Connection,
    registry: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """计算综合风险分。

    入参：
        conn: SQLite 连接
        registry: 指标注册表（含 name/classify/group）
    返回：
        dict: {
            "score": 32.5,
            "level": "YELLOW",
            "breakdown": {
                "曲线": {"score": 25.0, "weight": 25.0, "indicators": [{name,label,level,score}, ...]},
                ...
            },
            "missing": ["xxx", ...]   # 没数据被跳过的指标 name
        }
    """
    by_group: Dict[str, List[Dict[str, Any]]] = {}
    missing: List[str] = []

    for ind in registry:
        latest = dbmod.get_latest(conn, ind["name"])
        if latest is None:
            missing.append(ind["name"])
            continue
        try:
            level = ind["classify"](latest["value"])
            score = _LEVEL_SCORE.get(level, 0.0)
        except Exception:
            missing.append(ind["name"])
            continue
        by_group.setdefault(ind.get("group", "其他"), []).append({
            "name": ind["name"],
            "label": ind.get("label", ind["name"]),
            "level": level.value,
            "score": score,
            "value": latest["value"],
        })

    # 维度内平均，再按权重加权
    breakdown: Dict[str, Any] = {}
    weighted_sum = 0.0
    weight_total = 0.0

    for group, items in by_group.items():
        weight = _GROUP_WEIGHTS.get(group, 0.0)
        if not items:
            continue
        group_score = sum(i["score"] for i in items) / len(items)
        breakdown[group] = {
            "score": round(group_score, 2),
            "weight": weight,
            "indicators": items,
        }
        weighted_sum += group_score * weight
        weight_total += weight

    total = weighted_sum / weight_total if weight_total > 0 else 0.0
    return {
        "score": round(total, 2),
        "level": _classify_total(total),
        "breakdown": breakdown,
        "missing": missing,
    }


# ── 存储 ─────────────────────────────────────────────────────

_RISK_SCORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS risk_scores (
    date TEXT PRIMARY KEY,
    score REAL NOT NULL,
    level TEXT NOT NULL,
    breakdown_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def init_risk_score_schema(conn: sqlite3.Connection) -> None:
    with conn:
        conn.executescript(_RISK_SCORE_SCHEMA)


def upsert_risk_score(conn: sqlite3.Connection, date_iso: str, result: Dict[str, Any]) -> None:
    init_risk_score_schema(conn)
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {"breakdown": result["breakdown"], "missing": result["missing"]}
    with conn:
        conn.execute(
            """
            INSERT INTO risk_scores (date, score, level, breakdown_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                score=excluded.score,
                level=excluded.level,
                breakdown_json=excluded.breakdown_json,
                created_at=excluded.created_at
            """,
            (date_iso, result["score"], result["level"], json.dumps(payload, ensure_ascii=False), now),
        )


def get_latest_risk_score(conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    """取最新一条风险分；无 → None。

    breakdown_json 反序列化后铺平：返回顶层包含 score/level/breakdown/missing。
    """
    init_risk_score_schema(conn)
    cur = conn.execute(
        "SELECT date, score, level, breakdown_json, created_at FROM risk_scores ORDER BY date DESC LIMIT 1"
    )
    row = cur.fetchone()
    if row is None:
        return None
    d = dict(row)
    try:
        payload = json.loads(d["breakdown_json"])
        d["breakdown"] = payload.get("breakdown", {}) if isinstance(payload, dict) else {}
        d["missing"] = payload.get("missing", []) if isinstance(payload, dict) else []
    except Exception:
        d["breakdown"] = {}
        d["missing"] = []
    return d


def get_risk_series(
    conn: sqlite3.Connection, days: Optional[int] = None
) -> List[Dict[str, Any]]:
    """取风险分历史序列（按 date 升序）。

    入参：
        conn: 已开 schema 的连接
        days: 仅取最近 N 天；None=全部
    返回：
        list[dict] {date, score, level}
    """
    init_risk_score_schema(conn)
    if days is not None and days > 0:
        cur = conn.execute(
            """
            SELECT date, score, level FROM risk_scores
            WHERE date >= date('now', ?)
            ORDER BY date ASC
            """,
            (f"-{int(days)} days",),
        )
    else:
        cur = conn.execute(
            "SELECT date, score, level FROM risk_scores ORDER BY date ASC"
        )
    return [dict(r) for r in cur.fetchall()]


def run_and_store(
    conn: sqlite3.Connection,
    registry: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """计算 + 入库一气呵成。"""
    result = compute_score(conn, registry)
    today_iso = _date.today().isoformat()
    upsert_risk_score(conn, today_iso, result)
    log.info("risk_score 入库 date=%s score=%.2f level=%s", today_iso, result["score"], result["level"])
    return result
