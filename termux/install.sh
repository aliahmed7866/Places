#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

APP_DIR="${PLACES_APP_DIR:-$HOME/Places}"
REPO_URL="${PLACES_REPO_URL:-https://github.com/aliahmed7866/Places.git}"
STATE_DIR="$HOME/.local/state/places"
DATA_DIR="${PLACES_DATA_DIR:-$HOME/.local/share/places}"

pkg install -y python git >/dev/null

if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" fetch origin
  git -C "$APP_DIR" checkout main
  git -C "$APP_DIR" pull --ff-only origin main
fi

python -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip >/dev/null
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" >/dev/null
mkdir -p "$STATE_DIR" "$DATA_DIR"

cat > "$HOME/.local/bin/places" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec "$APP_DIR/termux/run.sh" "\$@"
EOF
chmod +x "$HOME/.local/bin/places" "$APP_DIR/termux/run.sh"

printf 'Places installed in %s\n' "$APP_DIR"
printf 'Data directory: %s\n' "$DATA_DIR"
printf 'Start with: places start\n'
printf 'Status with: places status\n'
printf 'Migrate AYCF data with: places migrate\n'
