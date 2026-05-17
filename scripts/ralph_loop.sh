#!/usr/bin/env bash
# ralph_loop.sh — Finance Radar 自动迭代循环
#
# 每轮启动一个全新 codebuddy 进程（新鲜上下文），喂入 .ralph/loop_prompt.md，
# 跑完一轮 PROMPT.md "工作循环 5 步"，然后做兜底校验：
#   - BLOCKED.md 存在 → 停
#   - pytest 红 → 写 BLOCKED.md 停
#   - .ralph/iteration.txt 没 +1 → 视为本轮失败，停
#
# 用法：
#   bash scripts/ralph_loop.sh             # 默认 10 轮
#   bash scripts/ralph_loop.sh 5           # 自定义最大轮数
#   bash scripts/ralph_loop.sh 10 --dry-run  # 不真跑 codebuddy，只打印命令（联调用）
#
# 设计参考：snarktank/ralph 的 ralph.sh，结合本项目已有 PROMPT/HANDOFF/PLAN 循环约定。
# 与 ralph 原版的差异详见 PROMPT.md §"自动 loop 模式"。

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MAX_ITER="${1:-10}"
DRY_RUN="${2:-}"

PYTHON_BIN="$ROOT/.venv/bin/python"
LOOP_PROMPT="$ROOT/.ralph/loop_prompt.md"
ITER_FILE="$ROOT/.ralph/iteration.txt"
PROGRESS_LOG="$ROOT/.ralph/progress.log"
BLOCKED_FILE="$ROOT/BLOCKED.md"
LOOP_LOG="$ROOT/.ralph/loop_runs.log"

# 颜色（仅 tty）
if [ -t 1 ]; then
  C_BLUE='\033[1;34m'; C_GREEN='\033[1;32m'; C_RED='\033[1;31m'; C_YELLOW='\033[1;33m'; C_RESET='\033[0m'
else
  C_BLUE=''; C_GREEN=''; C_RED=''; C_YELLOW=''; C_RESET=''
fi

log() { printf "${C_BLUE}[ralph-loop]${C_RESET} %s\n" "$*"; }
ok()  { printf "${C_GREEN}[ralph-loop]${C_RESET} %s\n" "$*"; }
warn(){ printf "${C_YELLOW}[ralph-loop]${C_RESET} %s\n" "$*"; }
err() { printf "${C_RED}[ralph-loop]${C_RESET} %s\n" "$*" >&2; }

# 前置检查
if [ ! -f "$LOOP_PROMPT" ]; then
  err "missing $LOOP_PROMPT, please create it first"
  exit 1
fi
if [ ! -x "$PYTHON_BIN" ]; then
  err "venv python not found: $PYTHON_BIN"
  exit 1
fi
if ! command -v codebuddy >/dev/null 2>&1; then
  err "找不到 codebuddy CLI"
  exit 1
fi

# 启动横幅
log "ralph_loop start"
log "max_iter=$MAX_ITER  root=$ROOT"
[ -n "$DRY_RUN" ] && warn "DRY-RUN mode: codebuddy will NOT be invoked"

START_TS="$(date +%Y-%m-%d_%H:%M:%S)"
echo "=== ralph_loop session $START_TS  max=$MAX_ITER ===" >> "$LOOP_LOG"

run_one_iter() {
  local round_no="$1"
  local prev_iter
  prev_iter="$(cat "$ITER_FILE" 2>/dev/null | tr -d '[:space:]' || echo 0)"

  log "---- round ${round_no}/${MAX_ITER}  (project iter=${prev_iter}) ----"

  # 1. BLOCKED 前置检查
  if [ -f "$BLOCKED_FILE" ]; then
    err "BLOCKED.md exists, abort. Resolve manually first."
    echo "[round $round_no @ $(date +%H:%M:%S)] aborted: BLOCKED.md exists" >> "$LOOP_LOG"
    return 2
  fi

  # 2. 启动 codebuddy 跑一轮
  local prompt_text
  prompt_text="$(cat "$LOOP_PROMPT")"

  if [ -n "$DRY_RUN" ]; then
    warn "DRY-RUN: skipping codebuddy invocation"
  else
    # -p 非交互；--max-turns 限单轮预算；-y 跳确认（loop 内不能有人按 y）
    # 用 stdin 传 prompt 避免命令行长度问题
    if ! printf "%s" "$prompt_text" | codebuddy -p \
          --max-turns 80 \
          -y \
          2>&1 | tee -a "$LOOP_LOG"; then
      err "codebuddy returned non-zero exit code"
      echo "[round $round_no @ $(date +%H:%M:%S)] codebuddy non-zero exit" >> "$LOOP_LOG"
      return 3
    fi
  fi

  # 3. 跑完后兜底校验
  # 3a. BLOCKED.md 出现 → agent 主动停
  if [ -f "$BLOCKED_FILE" ]; then
    warn "agent created BLOCKED.md, loop stops"
    echo "[round $round_no] BLOCKED.md created" >> "$LOOP_LOG"
    return 2
  fi

  # 3b. pytest 必须过
  log "fallback pytest -q ..."
  if ! "$PYTHON_BIN" -m pytest -q >/tmp/ralph_pytest.out 2>&1; then
    err "pytest failed, writing BLOCKED.md and stopping"
    {
      echo "# BLOCKED — pytest failed (ralph_loop fallback check)"
      echo
      echo "time: $(date)"
      echo "round: ${round_no}/${MAX_ITER} (project iter=${prev_iter})"
      echo
      echo "## pytest tail (last 50 lines)"
      echo
      echo '```'
      tail -50 /tmp/ralph_pytest.out
      echo '```'
    } > "$BLOCKED_FILE"
    echo "[round $round_no] pytest failed → BLOCKED.md" >> "$LOOP_LOG"
    return 3
  fi

  # 3c. iteration.txt 必须 +1
  local new_iter
  new_iter="$(cat "$ITER_FILE" 2>/dev/null | tr -d '[:space:]' || echo 0)"
  if [ "$new_iter" -le "$prev_iter" ]; then
    err "iteration.txt did not advance (${prev_iter} -> ${new_iter}); agent likely failed to finish"
    echo "[round $round_no] iteration not incremented ($prev_iter → $new_iter)" >> "$LOOP_LOG"
    return 4
  fi

  # 3d. progress.log 应该被追加（不强制，仅记录）
  local pg_lines
  pg_lines="$(wc -l < "$PROGRESS_LOG" 2>/dev/null || echo 0)"

  ok "round ${round_no} ok: iter ${prev_iter} -> ${new_iter}, progress.log lines=${pg_lines}"
  echo "[round $round_no] ok: iter $prev_iter → $new_iter" >> "$LOOP_LOG"
  return 0
}

# 主循环
EXIT_CODE=0
for i in $(seq 1 "$MAX_ITER"); do
  if run_one_iter "$i"; then
    continue
  else
    rc=$?
    if [ "$rc" = "2" ]; then
      warn "loop stopped manually/by-block (rc=2). Ran ${i} rounds."
      EXIT_CODE=0
    else
      err "loop aborted (rc=${rc}). Ran ${i} rounds."
      EXIT_CODE="${rc}"
    fi
    break
  fi
done

END_TS="$(date +%Y-%m-%d_%H:%M:%S)"
echo "=== ralph_loop session end $END_TS  exit=$EXIT_CODE ===" >> "$LOOP_LOG"
ok "ralph_loop done (exit=${EXIT_CODE}). log: $LOOP_LOG"
exit "$EXIT_CODE"
