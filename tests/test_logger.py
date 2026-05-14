"""logger 单元测试。"""
from __future__ import annotations

import logging
from pathlib import Path

from src.utils import logger as logmod


def test_get_logger_returns_logger_instance():
    log = logmod.get_logger("test.x")
    assert isinstance(log, logging.Logger)
    assert log.name == "test.x"


def test_log_path_under_project_logs_dir():
    p = logmod.log_path()
    assert p.name == "app.log"
    assert p.parent.name == "logs"


def test_handlers_attached_after_init():
    logmod.get_logger("test.y")
    root = logging.getLogger()
    # 至少 1 个 handler（stdout 必有；文件 handler 视环境）
    assert len(root.handlers) >= 1
    types = {type(h).__name__ for h in root.handlers}
    assert "StreamHandler" in types


def test_logger_writes_to_file(tmp_path, monkeypatch):
    """临时把日志目录指向 tmp_path，验证写文件路径生效。"""
    # 重置初始化标志，让 logger 重新装 handler
    monkeypatch.setattr(logmod, "_INITIALIZED", False)
    monkeypatch.setattr(logmod, "_LOG_DIR", tmp_path)
    monkeypatch.setattr(logmod, "_LOG_FILE", tmp_path / "app.log")

    log = logmod.get_logger("test.file")
    log.info("hello-finance-radar")

    # flush
    for h in logging.getLogger().handlers:
        h.flush()

    f = tmp_path / "app.log"
    assert f.exists(), "日志文件未创建"
    content = f.read_text(encoding="utf-8")
    assert "hello-finance-radar" in content
