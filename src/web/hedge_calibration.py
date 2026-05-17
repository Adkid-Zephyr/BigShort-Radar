"""政策对冲对比（视角 I）+ 阈值校准面板（视角 J）。

视角 I 政策对冲：
  THESIS §4.1 揭示的"延迟工具箱"盲区——风险面（VIX/HY OAS/SOFR-IORB 等）和
  对冲面（WALCL/ON RRP/TGA 等政策反应工具）应并排看。

视角 J 阈值校准：
  对每条指标统计在过去 N 年里 GREEN/YELLOW/RED 三档的天数占比。
  如果 RED 占比 >20%，说明阈值过敏感（频繁假警报）。
  如果 RED 占比 <1%，说明阈值过迟钝（错过真信号）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from src.compute.thresholds import Level, classify
from src.utils.logger import get_logger

log = get_logger(__name__)


# ── 视角 I：政策对冲 ────────────────────────────────────────

# 风险面 vs 对冲面分组（基于 group 字段）
RISK_GROUPS = ["波动率", "信用", "曲线", "流动性", "跨市场", "中国"]
HEDGE_GROUPS = ["政策"]


def split_risk_vs_hedge(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """把 dashboard rows 切分成"风险面"和"对冲面"两组。

    入参：
        rows: app._build_rows 输出
    返回：
        {"risk": [...rows...], "hedge": [...rows...]}
    """
    risk = []
    hedge = []
    for r in rows:
        g = r.get("group", "")
        if g in HEDGE_GROUPS:
            hedge.append(r)
        elif g in RISK_GROUPS:
            risk.append(r)
        # 其他 group 既不算风险也不算对冲
    return {"risk": risk, "hedge": hedge}


# ── 视角 J：阈值校准 ─────────────────────────────────────────

def calibrate_threshold(
    values: Sequence[float],
    threshold_low: Optional[float],
    threshold_high: Optional[float],
    direction: str = "up",
) -> Dict[str, Any]:
    """统计历史样本在三档的占比，并给出"过敏感/过迟钝/合理"判定。

    入参：
        values: 历史值序列
        threshold_low / threshold_high: 阈值
        direction: "up" / "down"
    返回：
        {
          "n_total": int,                # 有效样本数
          "n_green": int, "n_yellow": int, "n_red": int,
          "pct_green": float, "pct_yellow": float, "pct_red": float,
          "verdict": "ok" | "too_sensitive" | "too_dull",
          "verdict_reason": str,
        }
    """
    out = {
        "n_total": 0, "n_green": 0, "n_yellow": 0, "n_red": 0,
        "pct_green": 0.0, "pct_yellow": 0.0, "pct_red": 0.0,
        "verdict": "ok", "verdict_reason": "",
    }
    if threshold_low is None or threshold_high is None or not values:
        out["verdict"] = "no_data"
        out["verdict_reason"] = "缺数据或缺阈值"
        return out

    valid = []
    for v in values:
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f != f:  # NaN
            continue
        valid.append(f)

    n = len(valid)
    if n < 30:
        out["verdict"] = "no_data"
        out["verdict_reason"] = f"样本不足 30（实际 {n}）"
        return out

    n_g = n_y = n_r = 0
    for v in valid:
        lv = classify(v, low=threshold_low, high=threshold_high, direction=direction)
        if lv == Level.GREEN:
            n_g += 1
        elif lv == Level.YELLOW:
            n_y += 1
        elif lv == Level.RED:
            n_r += 1

    pct_g = n_g / n * 100
    pct_y = n_y / n * 100
    pct_r = n_r / n * 100

    if pct_r > 20:
        verdict = "too_sensitive"
        reason = f"RED 占比 {pct_r:.1f}% > 20%（频繁警报）"
    elif pct_r < 1 and n >= 365:
        verdict = "too_dull"
        reason = f"RED 占比 {pct_r:.1f}% < 1%（可能漏掉真信号）"
    else:
        verdict = "ok"
        reason = f"RED {pct_r:.1f}% / YELLOW {pct_y:.1f}% / GREEN {pct_g:.1f}% 看起来合理"

    out.update({
        "n_total": n, "n_green": n_g, "n_yellow": n_y, "n_red": n_r,
        "pct_green": pct_g, "pct_yellow": pct_y, "pct_red": pct_r,
        "verdict": verdict, "verdict_reason": reason,
    })
    return out
