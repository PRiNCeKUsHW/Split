#!/usr/bin/env bash
# Start FlatSplit for real use on the flat's LAN.
#
#   ./run.sh
#
# Serves on every interface, port 8000, so any phone on the WiFi can reach it.
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-.venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON=".venv/Scripts/python.exe"   # Windows layout
[ -x "$PYTHON" ] || PYTHON="python3"

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.prod}"

echo "Applying migrations…"
"$PYTHON" manage.py migrate --noinput

echo "Collecting static files…"
"$PYTHON" manage.py collectstatic --noinput --clear >/dev/null

IP="$("$PYTHON" -c 'from config.lan import primary_lan_ip; print(primary_lan_ip())')"
echo
echo "  FlatSplit is starting."
echo "  On this machine:  http://127.0.0.1:8000"
echo "  From a phone:     http://${IP}:8000"
echo

TUNNEL_PID=""
cleanup() {
  if [ -n "$TUNNEL_PID" ]; then
    kill "$TUNNEL_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

ENABLE_TUNNEL=0
for arg in "$@"; do
  if [ "$arg" = "--tunnel" ]; then
    ENABLE_TUNNEL=1
  fi
done
if [ "${TUNNEL:-0}" = "1" ]; then
  ENABLE_TUNNEL=1
fi

if [ "$ENABLE_TUNNEL" -eq 1 ]; then
  if command -v cloudflared >/dev/null 2>&1; then
    echo "  Starting Cloudflare Tunnel (look for the .trycloudflare.com URL below)..."
    echo
    cloudflared tunnel --url http://127.0.0.1:8000 &
    TUNNEL_PID=$!
    sleep 2
  else
    echo "  [!] 'cloudflared' not found. Run 'pkg install cloudflared' on Termux."
    echo
  fi
fi

# Gunicorn has no Windows support; Waitress is the stand-in there.
if "$PYTHON" -c "import gunicorn" 2>/dev/null; then
  "$PYTHON" -m gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --threads 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
else
  echo "Gunicorn not available (Windows?) — using Waitress."
  "$PYTHON" -m waitress --host=0.0.0.0 --port=8000 config.wsgi:application
fi

