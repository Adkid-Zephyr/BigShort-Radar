"""Flask Web 应用：薄渲染层。

只做：从 store 读数据 → 算颜色 → 渲染模板。
不做：拉数、算阈值（阈值用 indicators 模块的常量）。

注册新指标的方式：在 _INDICATOR_REGISTRY 加一行（name, classify_fn, label）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List

from flask import Flask, render_template

from src.compute.indicators import hy_oas as hyoas_ind
from src.compute.indicators import ig_oas as igoas_ind
from src.compute.indicators import vix as vix_ind
from src.compute.indicators import yield_curve as yc_ind
from src.compute.indicators import yield_curve_10y3m as yc3m_ind
from src.compute.thresholds import Level
from src.store import db as dbmod
from src.utils.config import load_settings
from src.utils.logger import get_logger

log = get_logger(__name__)

# 模板目录在项目根 templates/，不是 src/web/templates/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATE_DIR = _PROJECT_ROOT / "templates"


# ── 指标注册表 ────────────────────────────────────────────────
# 加一个新指标，只需在这里加一行
_INDICATOR_REGISTRY: List[Dict[str, Any]] = [
    {
        "name": vix_ind.NAME,
        "label": "VIX 恐慌指数",
        "classify": vix_ind.classify_value,
    },
    {
        "name": yc_ind.NAME,
        "label": "10Y-2Y 收益率曲线",
        "classify": yc_ind.classify_value,
    },
    {
        "name": yc3m_ind.NAME,
        "label": "10Y-3M 收益率曲线",
        "classify": yc3m_ind.classify_value,
    },
    {
        "name": hyoas_ind.NAME,
        "label": "HY OAS 高收益债利差",
        "classify": hyoas_ind.classify_value,
    },
    {
        "name": igoas_ind.NAME,
        "label": "IG OAS 投资级利差",
        "classify": igoas_ind.classify_value,
    },
]


# Level → 颜色（Tailwind 风格的色值，inline style 用）
_LEVEL_COLORS = {
    Level.GREEN: "#22c55e",
    Level.YELLOW: "#eab308",
    Level.RED: "#ef4444",
}


def _build_rows(conn) -> List[Dict[str, Any]]:
    """从 DB 拉每个已注册指标的最新值，组装渲染行。"""
    rows: List[Dict[str, Any]] = []
    for ind in _INDICATOR_REGISTRY:
        latest = dbmod.get_latest(conn, ind["name"])
        if latest is None:
            rows.append({
                "name": ind["name"],
                "label": ind["label"],
                "value": None,
                "level": None,
                "color": "#9ca3af",  # gray
                "date": None,
                "source": None,
                "ingested_at": None,
            })
            continue
        level = ind["classify"](latest["value"])
        rows.append({
            "name": ind["name"],
            "label": ind["label"],
            "value": latest["value"],
            "level": level.value,
            "color": _LEVEL_COLORS.get(level, "#9ca3af"),
            "date": latest["date"],
            "source": latest["source"],
            "ingested_at": latest["ingested_at"],
        })
    return rows


def create_app(db_path=None) -> Flask:
    """工厂函数：创建 Flask 应用。

    入参：
        db_path: 可选，覆盖默认 DB 路径（测试用）
    返回：
        Flask 应用实例
    """
    settings = load_settings()
    app = Flask(__name__, template_folder=str(_TEMPLATE_DIR))
    app.config["DB_PATH"] = db_path if db_path is not None else settings.db_path

    @app.route("/")
    def index():
        target = app.config["DB_PATH"]
        with dbmod.open_db(target) as conn:
            rows = _build_rows(conn)
        return render_template("index.html", rows=rows)

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    return app


if __name__ == "__main__":  # pragma: no cover
    settings = load_settings()
    create_app().run(
        host="127.0.0.1",
        port=settings.flask_port,
        debug=settings.flask_debug,
    )
