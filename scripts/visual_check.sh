#!/usr/bin/env bash
# visual_check.sh — Finance Radar dashboard 自检
#
# 用途：ralph loop 改完前端（templates/、src/web/）后调用，截图 + 抓 console + 抓 DOM 文本，
# 输出到 .ralph/visual_check_iter<N>/，由 agent 用 Read 读截图自己看图判断。
#
# 这是"防 agent 写完代码自吹自擂"的最后一道防线——靠多模态看图，不靠 pytest assert。
#
# 用法：
#   bash scripts/visual_check.sh           # 截当前 iteration 的图
#   bash scripts/visual_check.sh 35        # 强制指定 iter 号
#   bash scripts/visual_check.sh --no-flask  # 假定 Flask 已经在跑（不自启）
#
# 退出码：
#   0 = 截图成功（不代表 UI 对，agent 看图后判断）
#   1 = 环境错误（playwright-cli 缺失、Flask 起不来）
#   2 = 截图失败（页面 5xx、JS console 红等）

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# ── 参数解析 ────────────────────────────────────────────────
SKIP_FLASK=""
ITER_OVERRIDE=""
for arg in "$@"; do
  case "$arg" in
    --no-flask) SKIP_FLASK=1 ;;
    [0-9]*)     ITER_OVERRIDE="$arg" ;;
    *)          ;;
  esac
done

PYTHON_BIN="$ROOT/.venv/bin/python"
ITER_FILE="$ROOT/.ralph/iteration.txt"
ITER="${ITER_OVERRIDE:-$(cat "$ITER_FILE" 2>/dev/null | tr -d '[:space:]' || echo unknown)}"
OUT_DIR="$ROOT/.ralph/visual_check_iter${ITER}"
PORT=5050
URL="http://127.0.0.1:${PORT}/"

# 颜色
if [ -t 1 ]; then
  C_BLUE='\033[1;34m'; C_GREEN='\033[1;32m'; C_RED='\033[1;31m'; C_YELLOW='\033[1;33m'; C_RESET='\033[0m'
else
  C_BLUE=''; C_GREEN=''; C_RED=''; C_YELLOW=''; C_RESET=''
fi
log() { printf "${C_BLUE}[visual-check]${C_RESET} %s\n" "$*"; }
ok()  { printf "${C_GREEN}[visual-check]${C_RESET} %s\n" "$*"; }
warn(){ printf "${C_YELLOW}[visual-check]${C_RESET} %s\n" "$*"; }
err() { printf "${C_RED}[visual-check]${C_RESET} %s\n" "$*" >&2; }

# ── 前置检查 ────────────────────────────────────────────────
if ! command -v playwright-cli >/dev/null 2>&1; then
  err "playwright-cli not in PATH. Install: npm install -g @playwright/cli@latest"
  exit 1
fi
if [ ! -x "$PYTHON_BIN" ]; then
  err "venv python not found: $PYTHON_BIN"
  exit 1
fi

# 浏览器是否已装（chromium）。playwright-cli 用 ms-playwright cache。
PW_CACHE="${HOME}/Library/Caches/ms-playwright"
if [ ! -d "${PW_CACHE}" ] || [ -z "$(ls -A "${PW_CACHE}" 2>/dev/null | grep -E '^chromium' | head -1)" ]; then
  warn "chromium browser not installed in ${PW_CACHE}"
  warn "first-time setup needed. Run:"
  warn "  playwright-cli install-browser chromium"
  warn "  # or: npx playwright install chromium"
  warn "（在国内可能需要走代理或 npm registry mirror）"
  warn "skip this round; visual check unavailable until browser installed"
  exit 1
fi

mkdir -p "$OUT_DIR"
log "iter=${ITER}  out=${OUT_DIR}"

# ── 启动 Flask（除非 --no-flask）────────────────────────────
FLASK_PID=""
cleanup() {
  if [ -n "$FLASK_PID" ]; then
    log "stopping Flask (pid=$FLASK_PID)"
    kill "$FLASK_PID" 2>/dev/null || true
  fi
  playwright-cli -s=fr_visual close >/dev/null 2>&1 || true
}
trap cleanup EXIT

if [ -z "$SKIP_FLASK" ]; then
  log "starting Flask on :${PORT} ..."
  "$PYTHON_BIN" -m src.web.app >"$OUT_DIR/flask.log" 2>&1 &
  FLASK_PID=$!
  # 等服务就绪（最多 10s）
  for i in $(seq 1 20); do
    if curl -fsS "$URL" >/dev/null 2>&1; then
      ok "Flask ready (took ~${i}*0.5s)"
      break
    fi
    sleep 0.5
    if [ "$i" = "20" ]; then
      err "Flask did not become ready in 10s. See $OUT_DIR/flask.log"
      exit 1
    fi
  done
else
  log "--no-flask: assuming Flask already up at $URL"
  if ! curl -fsS "$URL" >/dev/null 2>&1; then
    err "$URL not reachable"
    exit 1
  fi
fi

# ── 用 playwright-cli 截图 + 抓 console + DOM 文本 ──────────
log "open browser session fr_visual"
playwright-cli -s=fr_visual close >/dev/null 2>&1 || true
playwright-cli -s=fr_visual open --browser=chromium "$URL" >"$OUT_DIR/pcli_open.log" 2>&1
playwright-cli -s=fr_visual resize 1440 900 >/dev/null 2>&1 || true

log "wait 2s for client-side render"
sleep 2

log "screenshot full page → dashboard.png"
playwright-cli -s=fr_visual screenshot --filename="$OUT_DIR/dashboard.png" >"$OUT_DIR/pcli_shot.log" 2>&1 || {
  err "screenshot failed (see $OUT_DIR/pcli_shot.log)"
  exit 2
}

log "snapshot DOM → dom.yaml"
playwright-cli -s=fr_visual snapshot --filename="$OUT_DIR/dom.yaml" >/dev/null 2>&1 || true

log "console log → console.txt"
playwright-cli -s=fr_visual console >"$OUT_DIR/console.txt" 2>&1 || true

log "page title via eval"
playwright-cli -s=fr_visual eval "document.title" >"$OUT_DIR/title.txt" 2>&1 || true

# ── 输出汇总 ────────────────────────────────────────────────
echo
ok "screenshots & artifacts saved to $OUT_DIR/"
ls -la "$OUT_DIR" | sed 's|^|  |'
echo
log "next step: agent should Read $OUT_DIR/dashboard.png and judge UI manually."
log "report goes to $ROOT/.ralph/visual_check_iter${ITER}.md (template at .ralph/visual_check_template.md)"

exit 0
