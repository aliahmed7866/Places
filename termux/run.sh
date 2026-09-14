#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

APP_DIR="${PLACES_APP_DIR:-$HOME/Places}"
STATE_DIR="$HOME/.local/state/places"
DATA_DIR="${PLACES_DATA_DIR:-$HOME/.local/share/places}"
PID_FILE="$STATE_DIR/places.pid"
LOG_FILE="$STATE_DIR/places.log"
PORT="${PLACES_PORT:-8084}"
mkdir -p "$STATE_DIR" "$DATA_DIR"

alive() {
  [ -f "$PID_FILE" ] || return 1
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

start() {
  if alive; then
    echo "Places already running (PID $(cat "$PID_FILE"))."
    return 0
  fi
  rm -f "$PID_FILE"
  cd "$APP_DIR"
  PLACES_DATA_DIR="$DATA_DIR" PLACES_PORT="$PORT" nohup "$APP_DIR/.venv/bin/python" app.py >>"$LOG_FILE" 2>&1 &
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
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "Places stopped."
}

status() {
  if alive; then
    echo "running pid=$(cat "$PID_FILE") url=http://127.0.0.1:$PORT"
    if command -v curl >/dev/null 2>&1; then
      curl -fsS "http://127.0.0.1:$PORT/health" || true
      echo
    fi
  else
    echo "stopped"
    return 1
  fi
}

update() {
  stop || true
  git -C "$APP_DIR" fetch origin
  git -C "$APP_DIR" checkout main
  git -C "$APP_DIR" pull --ff-only origin main
  "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" >/dev/null
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
  restart) stop || true; start ;;
  status) status ;;
  update) update ;;
  migrate) migrate "$@" ;;
  logs) tail -n "${2:-80}" "$LOG_FILE" ;;
  *) echo "Usage: places {start|stop|restart|status|update|migrate|logs}"; exit 2 ;;
esac
