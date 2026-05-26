#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

export HOME=/data/data/com.termux/files/home
export PREFIX=/data/data/com.termux/files/usr
export TMPDIR=/data/data/com.termux/files/usr/tmp
export PATH="$PREFIX/bin:/system/bin"
export LD_LIBRARY_PATH="$PREFIX/lib"

APP_DIR="$HOME/jhlwarehouse_hotdeal_crawler"
SCRIPT_SRC="/data/local/tmp/hotdeal_crawler.py"
CHALLENGE_SRC="/data/local/tmp/fmk_challenge.mjs"

apt update
apt install -y python nodejs
python -m pip install beautifulsoup4 requests

mkdir -p "$APP_DIR/logs"
cp "$SCRIPT_SRC" "$APP_DIR/hotdeal_crawler.py"
cp "$CHALLENGE_SRC" "$APP_DIR/fmk_challenge.mjs"

if [ ! -f "$APP_DIR/keywords.txt" ]; then
  printf '%s\n' 'MX KEYS' > "$APP_DIR/keywords.txt"
fi

cat > "$APP_DIR/run_once.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
export HOME=/data/data/com.termux/files/home
export PREFIX=/data/data/com.termux/files/usr
export TMPDIR=/data/data/com.termux/files/usr/tmp
export PATH="$PREFIX/bin:/system/bin"
export LD_LIBRARY_PATH="$PREFIX/lib"

APP_DIR="$HOME/jhlwarehouse_hotdeal_crawler"
if [ -f "$APP_DIR/.env" ]; then
  set -a
  . "$APP_DIR/.env"
  set +a
fi

cd "$APP_DIR"
python hotdeal_crawler.py
EOF

cat > "$APP_DIR/run_loop.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
export HOME=/data/data/com.termux/files/home
export PREFIX=/data/data/com.termux/files/usr
export TMPDIR=/data/data/com.termux/files/usr/tmp
export PATH="$PREFIX/bin:/system/bin"
export LD_LIBRARY_PATH="$PREFIX/lib"

APP_DIR="$HOME/jhlwarehouse_hotdeal_crawler"
if [ -f "$APP_DIR/.env" ]; then
  set -a
  . "$APP_DIR/.env"
  set +a
fi

RUN_MINUTE="${HOTDEAL_RUN_MINUTE:-3}"

termux-wake-lock || true
mkdir -p "$APP_DIR/logs"

next_run_epoch() {
  now="$(date +%s)"
  current_hour="$(date '+%Y-%m-%d %H')"
  target="$(date -d "$current_hour:$RUN_MINUTE:00" +%s)"
  if [ "$target" -le "$now" ]; then
    target="$((target + 3600))"
  fi
  printf '%s\n' "$target"
}

while true; do
  target="$(next_run_epoch)"
  now="$(date +%s)"
  sleep_seconds="$((target - now))"
  echo "Next hotdeal run: $(date -d "@$target" '+%Y-%m-%d %H:%M:%S %z') (sleep ${sleep_seconds}s)" >> "$APP_DIR/logs/loop.out"
  sleep "$sleep_seconds"
  "$APP_DIR/run_once.sh" >> "$APP_DIR/logs/hotdeal.log" 2>&1 || true
done
EOF

cat > "$APP_DIR/keyword.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

APP_DIR="/data/data/com.termux/files/home/jhlwarehouse_hotdeal_crawler"
KEYWORD_FILE="$APP_DIR/keywords.txt"
COMMAND="${1:-list}"
KEYWORD="${*:2}"

mkdir -p "$APP_DIR"
touch "$KEYWORD_FILE"

case "$COMMAND" in
  list)
    nl -ba "$KEYWORD_FILE"
    ;;
  add)
    if [ -z "$KEYWORD" ]; then
      echo "Usage: ./keyword.sh add \"MX KEYS\""
      exit 1
    fi
    if grep -Fxiq -- "$KEYWORD" "$KEYWORD_FILE"; then
      echo "Already exists: $KEYWORD"
    else
      printf '%s\n' "$KEYWORD" >> "$KEYWORD_FILE"
      echo "Added: $KEYWORD"
    fi
    ;;
  remove|rm|delete|del)
    if [ -z "$KEYWORD" ]; then
      echo "Usage: ./keyword.sh remove \"MX KEYS\""
      exit 1
    fi
    TMP_FILE="$KEYWORD_FILE.tmp"
    grep -Fxiv -- "$KEYWORD" "$KEYWORD_FILE" > "$TMP_FILE" || true
    mv "$TMP_FILE" "$KEYWORD_FILE"
    echo "Removed if present: $KEYWORD"
    ;;
  *)
    echo "Usage: ./keyword.sh list|add|remove [keyword]"
    exit 1
    ;;
esac
EOF

if [ ! -f "$APP_DIR/.env" ]; then
  cat > "$APP_DIR/.env" <<'EOF'
# EMAIL_PASSWORD=your_gmail_app_password
# EMAIL_SENDER=2joonh2@gmail.com
# EMAIL_TO=2joonh2@gmail.com
HOTDEAL_INTERVAL_SECONDS=3600
HOTDEAL_RUN_MINUTE=3
HOTDEAL_KEYWORD_FILE=keywords.txt
HOTDEAL_ALERT_ONLY=false
EOF
fi

chmod 700 "$APP_DIR/run_once.sh" "$APP_DIR/run_loop.sh" "$APP_DIR/keyword.sh"
"$APP_DIR/run_once.sh"
