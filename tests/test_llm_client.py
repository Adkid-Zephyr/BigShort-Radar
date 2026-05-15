"""LLM 客户端测试：mock requests，覆盖正常/缺 key/HTTP 错/解析错/异常。"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from src.fetch import llm_client
from src.utils.config import Settings


def _settings(key="testkey", base="https://api.example.com/v1", model="qwen-plus"):
    return Settings(
        fred_api_key=None,
        tz="Asia/Shanghai",
        flask_port=5050,
        flask_debug=False,
        db_path=Path("/tmp/x.sqlite"),
        logs_dir=Path("/tmp"),
        project_root=Path("/tmp"),
        llm_api_key=key,
        llm_base_url=base,
        llm_model=model,
    )


def _install_fake_requests(monkeypatch, *, status=200, body=None, exc=None):
    fake = types.ModuleType("requests")

    class FakeResp:
        def __init__(self):
            self.status_code = status
            self.text = ""
            self._body = body

        def json(self):
            if self._body is None:
                raise ValueError("no body")
            return self._body

    def post(url, headers=None, json=None, timeout=None):
        if exc is not None:
            raise exc
        return FakeResp()

    fake.post = post  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "requests", fake)


def test_chat_success(monkeypatch):
    body = {
        "choices": [
            {"message": {"role": "assistant", "content": "今日 VIX 17，处于平静区间。"}}
        ]
    }
    _install_fake_requests(monkeypatch, status=200, body=body)
    out = llm_client.chat(
        [{"role": "user", "content": "今天 VIX 怎么样"}],
        settings=_settings(),
    )
    assert out == "今日 VIX 17，处于平静区间。"


def test_chat_returns_none_when_no_key():
    out = llm_client.chat(
        [{"role": "user", "content": "x"}],
        settings=_settings(key=None),
    )
    assert out is None


def test_chat_returns_none_when_no_base():
    out = llm_client.chat(
        [{"role": "user", "content": "x"}],
        settings=_settings(base=None),
    )
    assert out is None


def test_chat_returns_none_on_http_error(monkeypatch):
    _install_fake_requests(monkeypatch, status=429, body={"error": "rate limit"})
    out = llm_client.chat(
        [{"role": "user", "content": "x"}],
        settings=_settings(),
    )
    assert out is None


def test_chat_returns_none_on_request_exception(monkeypatch):
    _install_fake_requests(monkeypatch, exc=RuntimeError("network down"))
    out = llm_client.chat(
        [{"role": "user", "content": "x"}],
        settings=_settings(),
    )
    assert out is None


def test_chat_returns_none_on_parse_error(monkeypatch):
    # 200 但返回结构不对
    _install_fake_requests(monkeypatch, status=200, body={"weird": "shape"})
    out = llm_client.chat(
        [{"role": "user", "content": "x"}],
        settings=_settings(),
    )
    assert out is None


def test_chat_uses_model_from_settings(monkeypatch):
    captured = {}

    fake = types.ModuleType("requests")

    class FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    def post(url, headers=None, json=None, timeout=None):
        captured["model"] = json["model"]
        captured["url"] = url
        return FakeResp()

    fake.post = post  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "requests", fake)

    llm_client.chat(
        [{"role": "user", "content": "x"}],
        settings=_settings(model="qwen-max"),
    )
    assert captured["model"] == "qwen-max"
    assert captured["url"].endswith("/chat/completions")
