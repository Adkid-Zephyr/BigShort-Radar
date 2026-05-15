#!/usr/bin/env bash
#
# 安装 / 卸载 / 查看 Finance Radar daily_fetch 的 launchd job。
# 用法：
#   bash scripts/install_launchd.sh install     # 装并启用
#   bash scripts/install_launchd.sh uninstall   # 卸载
#   bash scripts/install_launchd.sh status      # 查看运行状态
#   bash scripts/install_launchd.sh runonce     # 立即手动触发一次（不动 schedule）
#
# plist 安装到 ~/Library/LaunchAgents/com.financeradar.daily.plist
# 触发时间：北京 05:30（≈ 美东收盘半小时后）
set -euo pipefail

LABEL="com.financeradar.daily"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC_PLIST="$PROJECT_ROOT/scripts/com.financeradar.daily.plist"
DST_PLIST="$HOME/Library/LaunchAgents/com.financeradar.daily.plist"

cmd="${1:-status}"

case "$cmd" in
    install)
        echo "[install] 复制 plist 到 $DST_PLIST"
        mkdir -p "$HOME/Library/LaunchAgents"
        cp "$SRC_PLIST" "$DST_PLIST"
        # 已加载的话先卸载
        launchctl unload "$DST_PLIST" 2>/dev/null || true
        launchctl load "$DST_PLIST"
        echo "[install] 已加载，触发时间：每天 05:30（Asia/Shanghai）"
        echo "[install] 查看：launchctl list | grep $LABEL"
        ;;
    uninstall)
        if [[ -f "$DST_PLIST" ]]; then
            launchctl unload "$DST_PLIST" 2>/dev/null || true
            rm -f "$DST_PLIST"
            echo "[uninstall] 已移除 $DST_PLIST"
        else
            echo "[uninstall] 未安装"
        fi
        ;;
    status)
        if [[ -f "$DST_PLIST" ]]; then
            echo "[status] plist 存在：$DST_PLIST"
        else
            echo "[status] plist 未安装"
        fi
        echo "---launchctl list:"
        launchctl list | grep "$LABEL" || echo "  (未加载)"
        echo "---最后一次输出:"
        tail -n 5 "$PROJECT_ROOT/logs/launchd.out" 2>/dev/null || echo "  (无 stdout 日志)"
        echo "---最后一次错误:"
        tail -n 5 "$PROJECT_ROOT/logs/launchd.err" 2>/dev/null || echo "  (无 stderr 日志)"
        ;;
    runonce)
        echo "[runonce] 立即触发 daily_fetch（不影响 schedule）"
        cd "$PROJECT_ROOT"
        .venv/bin/python -m scripts.daily_fetch
        ;;
    *)
        echo "未知命令：$cmd"
        echo "用法：$0 {install|uninstall|status|runonce}"
        exit 1
        ;;
esac
