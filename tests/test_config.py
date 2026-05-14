"""config 单元测试。"""
from __future__ import annotations

import os

import pytest

from src.utils import config as cfg


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """每个测试隔离环境变量。"""
    for k in ("FRED_API_KEY", "TZ", "FLASK_PORT", "FLASK_DEBUG"):
        monkeypatch.delenv(k, raising=False)
    yield


def test_defaults_when_no_env_file(tmp_path):
    s = cfg.load_settings(env_path=tmp_path / "nope.env")
    assert s.fred_api_key is None
    assert s.tz == cfg.DEFAULT_TZ
    assert s.flask_port == cfg.DEFAULT_FLASK_PORT
    assert s.flask_debug is False
    assert s.db_path.name == "radar.sqlite"


def test_load_from_env_file(tmp_path):
    p = tmp_path / ".env"
    p.write_text(
        "FRED_API_KEY=abc123\nTZ=UTC\nFLASK_PORT=6000\nFLASK_DEBUG=1\n",
        encoding="utf-8",
    )
    s = cfg.load_settings(env_path=p)
    assert s.fred_api_key == "abc123"
    assert s.tz == "UTC"
    assert s.flask_port == 6000
    assert s.flask_debug is True


def test_existing_env_var_not_overridden(tmp_path, monkeypatch):
    monkeypatch.setenv("TZ", "America/New_York")
    p = tmp_path / ".env"
    p.write_text("TZ=Asia/Shanghai\n", encoding="utf-8")
    s = cfg.load_settings(env_path=p)
    # .env 不覆盖已有环境变量
    assert s.tz == "America/New_York"


def test_invalid_port_falls_back_to_default(tmp_path):
    p = tmp_path / ".env"
    p.write_text("FLASK_PORT=not_a_number\n", encoding="utf-8")
    s = cfg.load_settings(env_path=p)
    assert s.flask_port == cfg.DEFAULT_FLASK_PORT


def test_settings_is_frozen():
    s = cfg.load_settings(env_path=cfg.PROJECT_ROOT / "no-such-file.env")
    with pytest.raises(Exception):
        s.tz = "X"  # type: ignore[misc]


def test_quoted_values_stripped(tmp_path):
    p = tmp_path / ".env"
    p.write_text('FRED_API_KEY="quoted_key"\n', encoding="utf-8")
    s = cfg.load_settings(env_path=p)
    assert s.fred_api_key == "quoted_key"
