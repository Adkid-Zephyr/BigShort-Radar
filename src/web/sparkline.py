"""Sparkline SVG 渲染器（纯函数，无外部依赖）。

每条指标行右侧的 90 天微折线 + 三档阈值带背景。
设计原则：
  - 单文件 + 纯函数 + 零依赖（不引 plotly / matplotlib）
  - inline SVG 字符串，模板用 `r.sparkline_svg | safe` 直渲
  - 数据不足 N 个点（默认 10）→ 出灰色"积累中"占位

阈值带逻辑：
  - up 方向：值越高越危险 → 底色从下到上 GREEN/YELLOW/RED（值轴反转：SVG 坐标 y 向下）
  - down 方向：值越低越危险 → 底色从上到下 GREEN/YELLOW/RED

调用方负责传入历史值；本模块不查 DB。
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence

# 颜色（与 web/app.py _LEVEL_COLORS 对齐，但带透明度，避免压住折线）
_COLOR_GREEN_BG = "rgba(34,197,94,0.15)"
_COLOR_YELLOW_BG = "rgba(234,179,8,0.18)"
_COLOR_RED_BG = "rgba(239,68,68,0.18)"
_COLOR_LINE = "#e5e7eb"  # 浅灰白，与深色主题搭
_COLOR_DOT_LATEST = "#60a5fa"  # 蓝色高亮当前点
_COLOR_PLACEHOLDER = "#4b5563"

# 默认渲染参数
DEFAULT_WIDTH = 120
DEFAULT_HEIGHT = 28
MIN_POINTS = 10
DEFAULT_PADDING = 1


def _is_finite(v: float) -> bool:
    """判断 v 是合法有限浮点数（非 NaN / Inf / None）。"""
    if v is None:
        return False
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    return not (math.isnan(f) or math.isinf(f))


def _placeholder_svg(width: int, height: int, message: str) -> str:
    """生成"数据积累中"灰色占位 SVG。"""
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{message}">'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="none"/>'
        f'<text x="{width//2}" y="{height//2 + 4}" font-size="10" '
        f'fill="{_COLOR_PLACEHOLDER}" text-anchor="middle" font-family="-apple-system,sans-serif">'
        f'{message}</text></svg>'
    )


def build_sparkline_svg(
    values: Sequence[float],
    threshold_low: Optional[float] = None,
    threshold_high: Optional[float] = None,
    direction: str = "up",
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    min_points: int = MIN_POINTS,
) -> str:
    """生成 inline SVG 字符串：90 天微折线 + 三档阈值带 + 末点高亮。

    入参：
        values: 历史数值序列（按时间升序）。允许含 None/NaN，会被过滤
        threshold_low: GREEN/YELLOW 切点；None 则不画下阈值带
        threshold_high: YELLOW/RED 切点；None 则不画上阈值带
        direction: "up" (值越大越危险) 或 "down"（值越小越危险）
        width: SVG 宽度（默认 120）
        height: SVG 高度（默认 28）
        min_points: 少于此数视为"积累中"，出占位
    返回：
        inline SVG 字符串
    """
    # 过滤无效值
    clean = [float(v) for v in (values or []) if _is_finite(v)]
    n = len(clean)

    if n < min_points:
        return _placeholder_svg(width, height, f"积累中 ({n}/{min_points})")

    # 计算 y 轴范围（取 values + 阈值的 min/max，留 5% 余量）
    candidates = list(clean)
    if threshold_low is not None and _is_finite(threshold_low):
        candidates.append(float(threshold_low))
    if threshold_high is not None and _is_finite(threshold_high):
        candidates.append(float(threshold_high))
    v_min, v_max = min(candidates), max(candidates)
    if v_max == v_min:
        # 全部数值相同（极罕见）：硬扩 ±1 防 zero-div
        v_min -= 1.0
        v_max += 1.0
    v_span = v_max - v_min
    margin = v_span * 0.05
    v_min -= margin
    v_max += margin
    v_span = v_max - v_min

    # 坐标系：SVG y 向下，所以"显示值高 → y 小"，正常折线
    pad = DEFAULT_PADDING
    plot_w = width - 2 * pad
    plot_h = height - 2 * pad

    def y_of(value: float) -> float:
        # 值越大 → y 越小（顶部）
        return pad + (1.0 - (value - v_min) / v_span) * plot_h

    # 阈值带：把 [v_min, v_max] 这条值轴分成三段，分别用对应颜色填背景矩形
    bands = []
    if threshold_low is not None and threshold_high is not None and _is_finite(threshold_low) and _is_finite(threshold_high):
        tl, th = float(threshold_low), float(threshold_high)
        # GREEN 区 / YELLOW 区 / RED 区，每个区在 y 轴的范围
        # 注意：direction = "up"，值大=危险，所以 RED 在顶部（小 y）
        # direction = "down"，值小=危险，所以 RED 在底部（大 y）
        # 但带的位置由"阈值切点"决定，渲染时只看 y_of(threshold_*)：
        y_low = y_of(tl)
        y_high = y_of(th)
        # 注意 y_high < y_low 因为 th > tl 且 y_of 对值大返小 y
        # 但如果 direction = "down" 阈值定义反过来（GREEN > high），threshold_high 反而 < threshold_low 数值
        # 不强假设 tl < th；按 y 排序得稳健
        y_top = min(y_low, y_high)
        y_bot = max(y_low, y_high)
        # 顶部段（y < y_top）/ 中间段 / 底部段（y > y_bot）
        if direction == "up":
            top_color = _COLOR_RED_BG     # 高值在顶 → RED
            mid_color = _COLOR_YELLOW_BG
            bot_color = _COLOR_GREEN_BG
        else:  # "down"
            top_color = _COLOR_GREEN_BG   # 高值在顶 → GREEN
            mid_color = _COLOR_YELLOW_BG
            bot_color = _COLOR_RED_BG
        bands = [
            (pad, y_top - pad, top_color),
            (y_top, y_bot - y_top, mid_color),
            (y_bot, height - pad - y_bot, bot_color),
        ]

    # SVG 拼装
    parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="90 天微折线">'
    ]
    for y0, h, color in bands:
        if h > 0:
            parts.append(
                f'<rect x="0" y="{y0:.2f}" width="{width}" height="{h:.2f}" fill="{color}"/>'
            )

    # 折线 path：均分 x，y 由 value 决定
    if n >= 2:
        x_step = plot_w / (n - 1)
        path_d = []
        for i, v in enumerate(clean):
            x = pad + i * x_step
            y = y_of(v)
            cmd = "M" if i == 0 else "L"
            path_d.append(f"{cmd}{x:.2f},{y:.2f}")
        parts.append(
            f'<path d="{" ".join(path_d)}" fill="none" stroke="{_COLOR_LINE}" '
            f'stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        # 末点高亮（蓝色实心）
        last_x = pad + (n - 1) * x_step
        last_y = y_of(clean[-1])
        parts.append(
            f'<circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="2" fill="{_COLOR_DOT_LATEST}"/>'
        )

    parts.append("</svg>")
    return "".join(parts)
