#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Load saved defaults while keeping explicit installer overrides.
declare -A overrides=()
for key in PLACES_APP_DIR PLACES_PORT PLACES_DATA_DIR PLACES_DB_PATH; do
  if [ -n "${!key:-}" ]; then overrides[$key]="${!key}"; fi
done
[ ! -f "$HOME/.config/places/env" ] || source "$HOME/.config/places/env"
for key in "${!overrides[@]}"; do export "$key=${overrides[$key]}"; done
APP_DIR="${PLACES_APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
STATE_DIR="$HOME/.local/state/places"
DATA_DIR="${PLACES_DATA_DIR:-$HOME/.local/share/places}"

pkg install -y python git util-linux >/dev/null

python -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip >/dev/null
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" >/dev/null
mkdir -p "$STATE_DIR" "$DATA_DIR" "$HOME/.local/bin" "$HOME/.config/places"

PLACES_APP_DIR="$APP_DIR" "$APP_DIR/.venv/bin/python" "$APP_DIR/termux/register.py"

printf 'Places installed in %s\n' "$APP_DIR"
printf 'Data directory: %s\n' "$DATA_DIR"
printf 'Start with: places start\n'
printf 'Status with: places status\n'
printf 'Migrate AYCF data with: places migrate\n'
