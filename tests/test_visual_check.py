"""tests for scripts/visual_check.sh skeleton.

不真启 Flask / 不真打 playwright-cli（CI 上可能没装浏览器）。
只验：
  1) 脚本文件存在且可执行
  2) bash 语法 OK
  3) 关键命令片段都在脚本里（playwright-cli / screenshot / snapshot / console）
  4) 输出目录命名规则是 .ralph/visual_check_iter<N>/
  5) template 文件有 6 大 section
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "visual_check.sh"
TEMPLATE = ROOT / ".ralph" / "visual_check_template.md"


def test_script_exists_and_executable() -> None:
    assert SCRIPT.is_file(), f"missing {SCRIPT}"
    mode = SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, "visual_check.sh not executable"


def test_script_syntax_ok() -> None:
    """bash -n 仅做语法检查，不执行"""
    rc = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, f"bash syntax check failed: {rc.stderr}"


@pytest.mark.parametrize(
    "needle",
    [
        "playwright-cli",
        "screenshot",
        "snapshot",
        "console",
        "src.web.app",       # 启 Flask 的命令
        "visual_check_iter",  # 输出目录命名
        "--no-flask",         # 跳过自启 Flask 选项
    ],
)
def test_script_contains_key_commands(needle: str) -> None:
    text = SCRIPT.read_text()
    assert needle in text, f"missing command/flag '{needle}' in visual_check.sh"


def test_template_exists_and_has_sections() -> None:
    assert TEMPLATE.is_file(), f"missing {TEMPLATE}"
    text = TEMPLATE.read_text()
    # 6 个一级 section
    expected_sections = [
        "## 1. 改动摘要",
        "## 2. 自检命令",
        "## 3. 看图判断",
        "## 4. 看图发现的问题",
        "## 5. 结论",
        "## 6. TODO",
    ]
    for sec in expected_sections:
        assert sec in text, f"template missing section: {sec}"


def test_loop_prompt_mentions_visual_check() -> None:
    """loop_prompt.md 必须告诉 agent：改前端就跑 visual_check"""
    prompt = (ROOT / ".ralph" / "loop_prompt.md").read_text()
    assert "visual_check" in prompt, "loop_prompt.md should reference visual_check"


def test_gitignore_keeps_runtime_secrets_out() -> None:
    """仓库已转 private 后允许同步截图/数据库,但 key 与运行日志仍不能进 git。"""
    gitignore = (ROOT / ".gitignore").read_text()
    assert ".env" in gitignore, ".env must stay ignored"
    assert ".ralph/.token" in gitignore, "GitHub token must stay ignored"
    assert ".ralph/loop_runs.log" in gitignore, "loop runtime log should stay ignored"
