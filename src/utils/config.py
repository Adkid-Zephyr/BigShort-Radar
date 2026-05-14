"""集中配置：从 .env 读运行时变量 + 项目常量。

外部模块只通过本模块拿配置，不直接读 os.environ，便于测试与替换。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ── 项目级常量 ────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_DIR: Path = PROJECT_ROOT / "data"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
DB_PATH: Path = DATA_DIR / "radar.sqlite"

DEFAULT_FLASK_PORT: int = 5050  # 见 DECISIONS.md 2026-05-15
DEFAULT_TZ: str = "Asia/Shanghai"


def _load_dotenv_if_present(env_path: Path) -> None:
    """优先使用 python-dotenv；没装则用极简手写解析器。

    入参：
        env_path: .env 文件路径
    返回：无（副作用：写入 os.environ，不覆盖已存在的键）
    异常：
        文件不存在时静默跳过；解析异常忽略该行，不抛
    """
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env_path, override=False)
        return
    except ImportError:
        pass

    # 手写 fallback：只支持 KEY=VALUE，忽略注释与空行
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    """运行时配置快照。"""

    fred_api_key: Optional[str]
    tz: str
    flask_port: int
    flask_debug: bool
    db_path: Path
    logs_dir: Path
    project_root: Path


def _to_int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def load_settings(env_path: Optional[Path] = None) -> Settings:
    """读取 .env 并构造 Settings。

    入参：
        env_path: 可选，指定 .env 路径（测试常用）；默认为 PROJECT_ROOT/.env
    返回：
        Settings 实例（不可变）
    异常：
        无（缺键返回 None / 默认值）
    """
    target = env_path if env_path is not None else PROJECT_ROOT / ".env"
    _load_dotenv_if_present(target)

    return Settings(
        fred_api_key=os.environ.get("FRED_API_KEY") or None,
        tz=os.environ.get("TZ") or DEFAULT_TZ,
        flask_port=_to_int(os.environ.get("FLASK_PORT"), DEFAULT_FLASK_PORT),
        flask_debug=_to_bool(os.environ.get("FLASK_DEBUG"), False),
        db_path=DB_PATH,
        logs_dir=LOGS_DIR,
        project_root=PROJECT_ROOT,
    )
