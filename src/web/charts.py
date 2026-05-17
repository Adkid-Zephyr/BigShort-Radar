"""指标详情页大图渲染（Plotly 后端）。

设计原则：
  - 纯函数 build_indicator_chart_html(...) → 返回 plotly div HTML 字符串
  - 不嵌入 plotly.js（include_plotlyjs="cdn"），由模板里 cdn 标签共享
  - 阈值用水平线 + 三档区域填色（与 sparkline.py 心智一致）
  - 末点高亮蓝色
  - 失败时返回错误占位 div，不让页面崩

调用方：src/web/app.py 的 /indicator/<name> 路由
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from src.utils.logger import get_logger

log = get_logger(__name__)

# 颜色与 src/web/sparkline.py + app.py 对齐
_COLOR_LINE = "#e5e7eb"
_COLOR_LATEST_DOT = "#60a5fa"
_FILL_GREEN = "rgba(34,197,94,0.10)"
_FILL_YELLOW = "rgba(234,179,8,0.13)"
_FILL_RED = "rgba(239,68,68,0.13)"
_LINE_THRESHOLD = "rgba(156,163,175,0.5)"
_BG_PAPER = "#0d1014"
_BG_PLOT = "#11151a"
_TEXT = "#e5e7eb"
_AXIS = "rgba(229,231,235,0.15)"


def _placeholder_div(message: str) -> str:
    """无数据时的占位 div。"""
    return (
        f'<div class="chart-placeholder" '
        f'style="padding:60px 20px;text-align:center;color:#6b7280;'
        f'font-size:14px;border:1px dashed #374151;border-radius:8px;">'
        f'{message}</div>'
    )


def build_indicator_chart_html(
    name: str,
    label: str,
    dates: Sequence[str],
    values: Sequence[float],
    threshold_low: Optional[float] = None,
    threshold_high: Optional[float] = None,
    direction: str = "up",
    height: int = 460,
) -> str:
    """生成指标详情大图（Plotly div HTML）。

    入参：
        name: 指标 name（用作 div id 后缀）
        label: 中文显示名（图标题）
        dates: ISO 日期字符串序列，与 values 长度一致
        values: 对应数值
        threshold_low / threshold_high: 三档切点；任一缺失则不画阈值
        direction: "up" | "down"，决定三档填色方向
        height: SVG 高度
    返回：
        plotly div HTML 字符串（不含 <script src="plotly.js">，由模板共享 CDN）
    异常：
        不抛；plotly 失败时返回占位 div
    """
    if not dates or not values or len(dates) != len(values):
        return _placeholder_div(f"指标 {label} 暂无足够历史数据")

    if len(values) < 2:
        return _placeholder_div(f"{label} 历史数据不足 2 个点，等每日采集累积")

    try:
        import plotly.graph_objects as go
    except ImportError as e:
        log.error("plotly 未安装: %s", e)
        return _placeholder_div("plotly 未安装。pip install plotly")

    try:
        fig = go.Figure()

        # 主折线
        fig.add_trace(
            go.Scatter(
                x=list(dates),
                y=list(values),
                mode="lines",
                line=dict(color=_COLOR_LINE, width=1.5),
                name=label,
                hovertemplate="%{x|%Y-%m-%d}<br><b>%{y:.4f}</b><extra></extra>",
            )
        )

        # 末点蓝色高亮
        fig.add_trace(
            go.Scatter(
                x=[dates[-1]],
                y=[values[-1]],
                mode="markers",
                marker=dict(color=_COLOR_LATEST_DOT, size=8, line=dict(width=0)),
                showlegend=False,
                hovertemplate="当前 %{x|%Y-%m-%d}<br><b>%{y:.4f}</b><extra></extra>",
            )
        )

        # 阈值线 + 三档区域填色
        if (
            threshold_low is not None
            and threshold_high is not None
            and float(threshold_low) is not None
        ):
            tl = float(threshold_low)
            th = float(threshold_high)
            # 阈值线
            for tval, label_t in ((tl, f"low={tl}"), (th, f"high={th}")):
                fig.add_hline(
                    y=tval,
                    line_color=_LINE_THRESHOLD,
                    line_dash="dot",
                    line_width=1,
                    annotation_text=label_t,
                    annotation_position="top right",
                    annotation_font=dict(color=_LINE_THRESHOLD, size=10),
                )
            # 三档区域填色：取 y 轴 ± 范围扩展
            data_min = min(values)
            data_max = max(values)
            y_pad = max((data_max - data_min) * 0.05, 0.01)
            y_floor = min(data_min - y_pad, tl - y_pad)
            y_ceiling = max(data_max + y_pad, th + y_pad)
            # 三段区域：低 / 中 / 高（按 y 排序，再按 direction 填色）
            tlow = min(tl, th)
            thigh = max(tl, th)
            if direction == "up":
                # 值越大越危险：低=GREEN / 中=YELLOW / 高=RED
                fig.add_hrect(y0=y_floor, y1=tlow, fillcolor=_FILL_GREEN, line_width=0, layer="below")
                fig.add_hrect(y0=tlow, y1=thigh, fillcolor=_FILL_YELLOW, line_width=0, layer="below")
                fig.add_hrect(y0=thigh, y1=y_ceiling, fillcolor=_FILL_RED, line_width=0, layer="below")
            else:
                # 值越小越危险：低=RED / 中=YELLOW / 高=GREEN
                fig.add_hrect(y0=y_floor, y1=tlow, fillcolor=_FILL_RED, line_width=0, layer="below")
                fig.add_hrect(y0=tlow, y1=thigh, fillcolor=_FILL_YELLOW, line_width=0, layer="below")
                fig.add_hrect(y0=thigh, y1=y_ceiling, fillcolor=_FILL_GREEN, line_width=0, layer="below")

        # Layout
        fig.update_layout(
            title=dict(text=label, font=dict(color=_TEXT, size=16), x=0.02, xanchor="left"),
            height=height,
            margin=dict(l=50, r=30, t=50, b=50),
            paper_bgcolor=_BG_PAPER,
            plot_bgcolor=_BG_PLOT,
            font=dict(color=_TEXT, family="-apple-system, BlinkMacSystemFont, PingFang SC, sans-serif"),
            hovermode="x unified",
            showlegend=False,
            xaxis=dict(
                gridcolor=_AXIS,
                rangeslider=dict(visible=False),
                showspikes=True,
                spikecolor=_LINE_THRESHOLD,
                spikethickness=1,
                spikedash="dot",
            ),
            yaxis=dict(
                gridcolor=_AXIS,
                zeroline=True,
                zerolinecolor=_AXIS,
            ),
        )

        # 工具栏配置：保留 zoom/pan/reset，去掉 lasso/select 等
        config = {
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
            "toImageButtonOptions": {"format": "png", "filename": f"chart_{name}", "height": 600, "width": 1200},
        }

        return fig.to_html(
            include_plotlyjs="cdn",
            full_html=False,
            div_id=f"chart_{name}",
            config=config,
        )
    except Exception as e:  # noqa: BLE001 — plotly 内部异常一律降级
        log.error("plotly 渲染 %s 失败: %s", name, e)
        return _placeholder_div(f"图表渲染失败: {e}")
