"""5 个崩盘剧本检测器（THESIS §3.2 核心 + 视角 G 组合信号）。

每个剧本是一组规则的逻辑组合（多个指标同时满足条件）。
当前实现简化版：每个规则就是一个 (name, condition_fn) 对。

调用方：app.py 主 dashboard 顶部展示活跃剧本。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from src.utils.logger import get_logger

log = get_logger(__name__)

# 单个规则：取主 DB latest dict（含 value/level）+ 指标 name → True/False
Rule = Tuple[str, str, Callable[[Optional[Dict[str, Any]]], bool]]


def _val(latest: Optional[Dict[str, Any]]) -> Optional[float]:
    if latest is None:
        return None
    try:
        return float(latest["value"])
    except (TypeError, ValueError, KeyError):
        return None


def _is_red(latest: Optional[Dict[str, Any]], classify_fn: Optional[Callable] = None) -> bool:
    """从 latest dict 判 RED。优先用 classify_fn，否则不可判返 False。"""
    if latest is None:
        return False
    v = _val(latest)
    if v is None or classify_fn is None:
        return False
    try:
        from src.compute.thresholds import Level
        return classify_fn(v) == Level.RED
    except Exception:
        return False


def _is_yellow_or_red(latest: Optional[Dict[str, Any]], classify_fn: Optional[Callable] = None) -> bool:
    if latest is None or classify_fn is None:
        return False
    v = _val(latest)
    if v is None:
        return False
    try:
        from src.compute.thresholds import Level
        return classify_fn(v) in (Level.YELLOW, Level.RED)
    except Exception:
        return False


# ── 5 个剧本定义 ─────────────────────────────────────────────

# 每个剧本：name + 中文 label + 核心规则字典 {indicator_name: 条件描述}
SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "A_dollar_squeeze",
        "label": "A. 美元荒 / 回购市场炸",
        "thesis_ref": "THESIS §3.2 剧本 A",
        "description": "DXY 强 + USDJPY 高 + SOFR-IORB 异常 + ON RRP 缓冲耗尽",
        "rules": [
            ("dxy_broad", "≥YELLOW"),
            ("usdjpy", "≥YELLOW"),
            ("sofr_iorb", "≥YELLOW"),
            ("on_rrp", "RED"),
        ],
        "min_match": 3,  # 4 条中至少 3 条触发就算激活
    },
    {
        "id": "B_basis_blow",
        "label": "B. 国债基差爆仓",
        "thesis_ref": "THESIS §3.2 剧本 B",
        "description": "SOFR-IORB 突变 + 10Y-2Y 倒挂 + WALCL 救市量级",
        "rules": [
            ("sofr_iorb", "RED"),
            ("yield_curve_10y2y", "RED"),
            ("walcl", "≥YELLOW"),
        ],
        "min_match": 2,
    },
    {
        "id": "C_japan_carry",
        "label": "C. 日本 carry trade 解除",
        "thesis_ref": "THESIS §3.2 剧本 C",
        "description": "USDJPY 突破 + 日本 10Y 飙 + 中国资本外流",
        "rules": [
            ("usdjpy", "≥YELLOW"),
            ("jp_10y", "≥YELLOW"),
            ("china_fx_reserves", "≥YELLOW"),
        ],
        "min_match": 2,
    },
    {
        "id": "D_ai_bubble",
        "label": "D. AI 资本支出循环断裂",
        "thesis_ref": "THESIS §3.2 剧本 D",
        "description": "VIX 期限 backwardation + VVIX 高 + SKEW 高（黑天鹅定价升）",
        "rules": [
            ("vix_term_structure", "≥YELLOW"),
            ("vvix", "≥YELLOW"),
            ("skew", "≥YELLOW"),
        ],
        "min_match": 2,
    },
    {
        "id": "E_credit_lag",
        "label": "E. 信用 + 估值滞后崩",
        "thesis_ref": "THESIS §3.2 剧本 E",
        "description": "HY OAS 走阔 + IG OAS 走阔（同步 = 系统性信用收缩）",
        "rules": [
            ("hy_oas", "≥YELLOW"),
            ("ig_oas", "≥YELLOW"),
        ],
        "min_match": 2,  # 全部 2 条都要触发
    },
]


def evaluate_scenarios(
    indicator_states: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """评估 5 个剧本的激活程度。

    入参：
        indicator_states: {name: {"latest": {...}, "classify": fn}}
            其中 latest 是 dbmod.get_latest 输出，classify 是 indicator 模块的 classify_value
    返回：
        list of dicts: {id, label, description, thesis_ref, matched, total, level, active, hits}
        level: "active"（match>=min_match）/ "watch"（>0 但不到 min）/ "quiet"（0）
    """
    out: List[Dict[str, Any]] = []
    for scenario in SCENARIOS:
        hits: List[str] = []
        total = len(scenario["rules"])
        for ind_name, condition in scenario["rules"]:
            state = indicator_states.get(ind_name) or {}
            latest = state.get("latest")
            classify_fn = state.get("classify")
            if condition == "RED":
                ok = _is_red(latest, classify_fn)
            elif condition in ("≥YELLOW", "YELLOW_OR_RED"):
                ok = _is_yellow_or_red(latest, classify_fn)
            else:
                ok = False
            if ok:
                hits.append(ind_name)

        matched = len(hits)
        active = matched >= scenario["min_match"]
        if active:
            level = "active"
        elif matched > 0:
            level = "watch"
        else:
            level = "quiet"

        out.append({
            "id": scenario["id"],
            "label": scenario["label"],
            "description": scenario["description"],
            "thesis_ref": scenario["thesis_ref"],
            "matched": matched,
            "total": total,
            "min_match": scenario["min_match"],
            "level": level,
            "active": active,
            "hits": hits,
        })
    return out
