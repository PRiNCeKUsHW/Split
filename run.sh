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

# Gunicorn has no Windows support; Waitress is the stand-in there.
if "$PYTHON" -c "import gunicorn" 2>/dev/null; then
  exec "$PYTHON" -m gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --threads 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
else
  echo "Gunicorn not available (Windows?) — using Waitress."
  exec "$PYTHON" -m waitress --host=0.0.0.0 --port=8000 config.wsgi:application
fi
