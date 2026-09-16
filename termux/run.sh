#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

CONFIG_FILE="$HOME/.config/places/env"
[ ! -f "$CONFIG_FILE" ] || source "$CONFIG_FILE"
APP_DIR="${PLACES_APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE_DIR="$HOME/.local/state/places"
DATA_DIR="${PLACES_DATA_DIR:-$HOME/.local/share/places}"
PID_FILE="$STATE_DIR/places.pid"
LOG_FILE="$STATE_DIR/places.log"
PORT="${PLACES_PORT:-8084}"
mkdir -p "$STATE_DIR" "$DATA_DIR"
exec 9>"$STATE_DIR/control.lock"
case "${1:-status}" in
  status|logs) ;;
  *) flock -w 15 9 || { echo "Another Places command is still running." >&2; exit 1; } ;;
esac

alive() {
  [ -f "$PID_FILE" ] || return 1
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  [[ "$pid" =~ ^[0-9]+$ ]] && [ "$pid" -gt 1 ] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  [ -r "/proc/$pid/cmdline" ] || return 1
  tr '\0' '\n' < "/proc/$pid/cmdline" | grep -Fxq "$APP_DIR/app.py"
}

start() {
  if alive; then
    echo "Places already running (PID $(cat "$PID_FILE"))."
    return 0
  fi
  rm -f "$PID_FILE"
  cd "$APP_DIR"
  PLACES_DATA_DIR="$DATA_DIR" PLACES_PORT="$PORT" nohup "$APP_DIR/.venv/bin/python" "$APP_DIR/app.py" >>"$LOG_FILE" 2>&1 9>&- &
  echo $! > "$PID_FILE"
  sleep 1
  if alive; then
    echo "Places started at http://127.0.0.1:$PORT (PID $(cat "$PID_FILE"))."
  else
    echo "Places failed to start. Recent log:"
    tail -30 "$LOG_FILE" 2>/dev/null || true
    exit 1
  fi
}

stop() {
  if ! alive; then
    rm -f "$PID_FILE"
    echo "Places is not running."
    return 0
  fi
  local pid
  pid="$(cat "$PID_FILE")"
  kill "$pid"
  for _ in 1 2 3 4 5; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done
  if alive; then kill -9 "$pid" 2>/dev/null || true; fi
  rm -f "$PID_FILE"
  echo "Places stopped."
}

status() {
  if alive; then
    echo "running pid=$(cat "$PID_FILE") url=http://127.0.0.1:$PORT"

  else
    echo "stopped"
    return 1
  fi
}

update() {
  [ -z "$(git -C "$APP_DIR" status --porcelain --untracked-files=no)" ] || { echo "Local changes found; update stopped." >&2; return 1; }
  GIT_TERMINAL_PROMPT=0 git -C "$APP_DIR" fetch origin
  [ "$(git -C "$APP_DIR" branch --show-current)" = main ] || { echo "Switch to the Places main branch before updating." >&2; return 1; }
  git -C "$APP_DIR" merge --ff-only origin/main
  "$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt" >/dev/null
  stop
  start
}

migrate() {
  shift || true
  cd "$APP_DIR"
  PLACES_DATA_DIR="$DATA_DIR" "$APP_DIR/.venv/bin/python" migrate_aycf.py "$@"
}

case "${1:-status}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  update) update ;;
  migrate) migrate "$@" ;;
  logs) tail -n "${2:-80}" "$LOG_FILE" ;;
  *) echo "Usage: places {start|stop|restart|status|update|migrate|logs}"; exit 2 ;;
esac
