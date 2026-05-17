"""风险矩阵热力图（视角 D）+ 综合温度计 2 年时间线（视角 E）。

设计原则：
  - 纯函数，不查 DB（接受 dates/values 参数）
  - 用 plotly 后端生成 div HTML，CDN 共享
  - 热力图：横轴日期 / 纵轴指标 / 单元格按 level 着色
  - 时间线：x 轴 2 年日期 / y 轴 0-100 综合分 / 三档背景带

调用方：app.py 的 /heatmap 与 /timeline 路由
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from src.compute.thresholds import Level, classify
from src.utils.logger import get_logger

log = get_logger(__name__)

# 颜色与其他模块对齐
_COLOR_GREEN = "rgba(34,197,94,0.7)"
_COLOR_YELLOW = "rgba(234,179,8,0.7)"
_COLOR_RED = "rgba(239,68,68,0.85)"
_COLOR_NA = "rgba(75,85,99,0.4)"
_BG_PAPER = "#0d1014"
_BG_PLOT = "#11151a"
_TEXT = "#e5e7eb"
_AXIS = "rgba(229,231,235,0.15)"


def _level_to_int(level: Optional[Level]) -> int:
    """level → 数值（plotly heatmap 要求数字 z 矩阵）。"""
    if level is None:
        return -1
    return {Level.GREEN: 0, Level.YELLOW: 1, Level.RED: 2}[level]


def _placeholder(message: str) -> str:
    return (
        f'<div style="padding:80px 20px;text-align:center;color:#6b7280;'
        f'font-size:14px;border:1px dashed #374151;border-radius:8px;">'
        f'{message}</div>'
    )


def build_heatmap_html(
    indicators: Sequence[Dict[str, Any]],
    height: int = 600,
) -> str:
    """指标 × 日期热力图。

    入参：
        indicators: list of dict，每条含：
          - "name": 指标 name
          - "label": 中文显示名
          - "dates": list[str] ISO 升序
          - "values": list[float] 同长度
          - "threshold_low" / "threshold_high" / "direction"
        height: SVG 高度
    返回：plotly div HTML（含 plotly.js cdn）
    """
    if not indicators:
        return _placeholder("无数据")

    try:
        import plotly.graph_objects as go
    except ImportError:
        return _placeholder("plotly 未安装")

    try:
        # 找所有指标的并集日期（升序）
        all_dates: set = set()
        for ind in indicators:
            all_dates.update(ind.get("dates", []))
        sorted_dates = sorted(all_dates)
        if not sorted_dates:
            return _placeholder("无数据")

        # 每条指标按并集日期对齐，生成 z 矩阵
        labels = [ind["label"] for ind in indicators]
        z_matrix: List[List[int]] = []
        text_matrix: List[List[str]] = []
        for ind in indicators:
            tl = ind.get("threshold_low")
            th = ind.get("threshold_high")
            direction = ind.get("direction", "up")
            d_to_v = dict(zip(ind.get("dates", []), ind.get("values", [])))
            row_z: List[int] = []
            row_text: List[str] = []
            for d in sorted_dates:
                v = d_to_v.get(d)
                if v is None or tl is None or th is None:
                    row_z.append(-1)
                    row_text.append(f"{d}<br>{ind['label']}<br>无数据")
                    continue
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    row_z.append(-1)
                    row_text.append(f"{d}<br>{ind['label']}<br>无数据")
                    continue
                if fv != fv:  # NaN
                    row_z.append(-1)
                    row_text.append(f"{d}<br>{ind['label']}<br>无数据")
                    continue
                lv = classify(fv, low=tl, high=th, direction=direction)
                row_z.append(_level_to_int(lv))
                row_text.append(f"{d}<br>{ind['label']}<br>{lv.value} ({fv:.4g})")
            z_matrix.append(row_z)
            text_matrix.append(row_text)

        # 自定义颜色映射：-1=灰 / 0=绿 / 1=黄 / 2=红
        # plotly 的 colorscale 走 0-1 normalized
        # 用离散颜色：colorscale = [(0, gray), (0.25, gray), (0.25, green), (0.5, green), (0.5, yellow), ...]
        # 简化：用范围 -1~2，映射 4 个颜色
        colorscale = [
            [0.0, _COLOR_NA],     # -1
            [0.33, _COLOR_NA],
            [0.34, _COLOR_GREEN], # 0
            [0.55, _COLOR_GREEN],
            [0.56, _COLOR_YELLOW],# 1
            [0.78, _COLOR_YELLOW],
            [0.79, _COLOR_RED],   # 2
            [1.0, _COLOR_RED],
        ]

        fig = go.Figure(
            data=go.Heatmap(
                z=z_matrix,
                x=sorted_dates,
                y=labels,
                text=text_matrix,
                hovertemplate="%{text}<extra></extra>",
                colorscale=colorscale,
                zmin=-1,
                zmax=2,
                showscale=False,
                xgap=1,
                ygap=2,
            )
        )
        fig.update_layout(
            height=height,
            margin=dict(l=160, r=20, t=20, b=80),
            paper_bgcolor=_BG_PAPER,
            plot_bgcolor=_BG_PLOT,
            font=dict(color=_TEXT, family="-apple-system, BlinkMacSystemFont, PingFang SC, sans-serif", size=11),
            xaxis=dict(gridcolor=_AXIS, type="date"),
            yaxis=dict(gridcolor=_AXIS, autorange="reversed"),
        )
        config = {"displayModeBar": False, "displaylogo": False}
        return fig.to_html(include_plotlyjs="cdn", full_html=False, div_id="heatmap_main", config=config)
    except Exception as e:  # noqa: BLE001
        log.error("heatmap 渲染失败: %s", e)
        return _placeholder(f"渲染失败: {e}")


def build_risk_timeline_html(
    dates: Sequence[str],
    scores: Sequence[float],
    height: int = 460,
) -> str:
    """综合温度计 2 年时间线。

    入参：
        dates: ISO 日期升序
        scores: 同长度 0-100 综合分
        height: SVG 高度
    返回：plotly div HTML
    """
    if not dates or not scores or len(dates) != len(scores):
        return _placeholder("综合温度计历史数据不足")
    if len(scores) < 2:
        return _placeholder("综合温度计累积中（至少需 2 个数据点）")

    try:
        import plotly.graph_objects as go
    except ImportError:
        return _placeholder("plotly 未安装")

    try:
        fig = go.Figure()

        # 三档背景带
        fig.add_hrect(y0=0, y1=25, fillcolor="rgba(34,197,94,0.10)", line_width=0, layer="below")
        fig.add_hrect(y0=25, y1=65, fillcolor="rgba(234,179,8,0.10)", line_width=0, layer="below")
        fig.add_hrect(y0=65, y1=100, fillcolor="rgba(239,68,68,0.13)", line_width=0, layer="below")

        # 主折线
        fig.add_trace(
            go.Scatter(
                x=list(dates),
                y=list(scores),
                mode="lines+markers",
                line=dict(color="#e5e7eb", width=2),
                marker=dict(size=4, color="#60a5fa"),
                name="综合分",
                hovertemplate="%{x|%Y-%m-%d}<br>综合分 <b>%{y:.1f}</b><extra></extra>",
            )
        )

        # 切点水平线
        for ytv, yvl in ((25, "GREEN/YELLOW=25"), (65, "YELLOW/RED=65")):
            fig.add_hline(
                y=ytv, line_color="rgba(156,163,175,0.5)", line_dash="dot", line_width=1,
                annotation_text=yvl, annotation_position="top right",
                annotation_font=dict(color="#9ca3af", size=10),
            )

        fig.update_layout(
            height=height,
            margin=dict(l=50, r=30, t=30, b=50),
            paper_bgcolor=_BG_PAPER,
            plot_bgcolor=_BG_PLOT,
            font=dict(color=_TEXT, family="-apple-system, BlinkMacSystemFont, PingFang SC, sans-serif"),
            hovermode="x unified",
            showlegend=False,
            xaxis=dict(gridcolor=_AXIS, type="date"),
            yaxis=dict(gridcolor=_AXIS, range=[0, 100]),
        )
        config = {"displayModeBar": True, "displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}
        return fig.to_html(include_plotlyjs="cdn", full_html=False, div_id="timeline_main", config=config)
    except Exception as e:  # noqa: BLE001
        log.error("timeline 渲染失败: %s", e)
        return _placeholder(f"渲染失败: {e}")
