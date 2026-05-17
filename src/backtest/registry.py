"""回测专用 registry：扩展自主流程 19 条 + vix_fred + ted_spread 仅回测用。

设计：
  - 主流程 _INDICATOR_REGISTRY 不动（PROMPT 暂停清单"不改已定义指标"）
  - 这里 BACKTEST_INDICATORS = 主 registry + 2 条仅历史回测用的指标
  - vix_fred 用 FRED:VIXCLS 拿到 1990 年起完整 VIX 历史（绕开 yahoo 限速）
  - ted_spread 用 FRED:TEDRATE（3M LIBOR - 3M T-Bill）作为 SOFR-IORB 的 2018 前代理
    （LIBOR USD 系列 USD3MTD156N 已停发不可拉，TED Spread 是经典美元荒度量）

回测时遇到 vix 与 vix_fred 同名同 group 的话由调用方决定优先级（推荐用 vix_fred）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.compute.indicators import vix as vix_ind
from src.compute.thresholds import Level, classify
from src.web.app import _INDICATOR_REGISTRY


# ── 仅回测用：vix_fred ───────────────────────────────────────

_VIX_FRED_LOW = vix_ind.THRESHOLD_LOW   # 复用 VIX 阈值
_VIX_FRED_HIGH = vix_ind.THRESHOLD_HIGH


def _vix_fred_classify(value: float) -> Level:
    return classify(value, low=_VIX_FRED_LOW, high=_VIX_FRED_HIGH, direction="up")


# ── 仅回测用：ted_spread ─────────────────────────────────────

# TED Spread = 3M LIBOR - 3M T-Bill（FRED:TEDRATE）
# 阈值（基于 1986-2022 历史，单位 %）：
#   GREEN  < 0.50    正常稳态
#   YELLOW 0.50-1.00 紧张
#   RED    > 1.00    显著美元荒（2008 雷曼周一度 4.58%）
_TED_LOW = 0.50
_TED_HIGH = 1.00


def _ted_spread_classify(value: float) -> Level:
    return classify(value, low=_TED_LOW, high=_TED_HIGH, direction="up")


# ── BACKTEST_INDICATORS ──────────────────────────────────────

# 主流程 19 条 + 2 条仅回测扩展
BACKTEST_INDICATORS: List[Dict[str, Any]] = [
    *_INDICATOR_REGISTRY,
    {
        "name": "vix_fred",
        "label": "VIX (FRED:VIXCLS, 仅回测)",
        "source": "FRED:VIXCLS",
        "classify": _vix_fred_classify,
        "group": "波动率",
        "threshold_low": _VIX_FRED_LOW,
        "threshold_high": _VIX_FRED_HIGH,
        "direction": "up",
        "_backtest_only": True,
    },
    {
        "name": "ted_spread",
        "label": "TED Spread (3M LIBOR - 3M T-Bill, 仅回测)",
        "source": "FRED:TEDRATE",
        "classify": _ted_spread_classify,
        "group": "流动性",
        "threshold_low": _TED_LOW,
        "threshold_high": _TED_HIGH,
        "direction": "up",
        "_backtest_only": True,
    },
]


def main_only_indicators() -> List[Dict[str, Any]]:
    """返回主流程 registry 不含 _backtest_only=True 的指标。"""
    return [ind for ind in BACKTEST_INDICATORS if not ind.get("_backtest_only")]


def backtest_only_indicators() -> List[Dict[str, Any]]:
    """返回仅回测用的指标。"""
    return [ind for ind in BACKTEST_INDICATORS if ind.get("_backtest_only")]

