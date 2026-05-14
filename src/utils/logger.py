"""统一 logging。

输出 stdout + logs/app.log。所有模块用 `get_logger(__name__)` 拿实例。
"""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_FILE = _LOG_DIR / "app.log"

_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"

_INITIALIZED = False


def _init_root_logger() -> None:
    """初始化根 logger（只跑一次）。

    入参：无
    返回：无
    异常：写日志目录失败时回退到仅 stdout，不抛
    """
    global _INITIALIZED
    if _INITIALIZED:
        return

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # 清掉默认 handler，避免重复输出
    root.handlers.clear()

    formatter = logging.Formatter(_FMT, datefmt=_DATEFMT)

    # stdout
    sh = logging.StreamHandler(stream=sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)
    root.addHandler(sh)

    # 文件（带轮转，单文件 1MB，保留 5 份）
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            _LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        root.addHandler(fh)
    except OSError as e:
        # 写文件失败不让程序崩；只在 stdout 留痕
        root.warning("logger 文件 handler 初始化失败: %s（仅 stdout 输出）", e)

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """获取一个模块级 logger。

    入参：
        name: 模块名，通常传 __name__
    返回：
        logging.Logger 实例，已绑定 stdout 与文件 handler
    异常：
        无（初始化失败已在内部静默降级）
    """
    _init_root_logger()
    return logging.getLogger(name)


def log_path() -> Path:
    """返回当前日志文件路径。便于测试与诊断。"""
    return _LOG_FILE
