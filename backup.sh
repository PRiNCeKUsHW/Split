#!/usr/bin/env bash
# Back up the database and the uploaded receipts.
#
#   ./backup.sh [destination-directory]
#
# SQLite is a single file, but copying it while the app is writing can give
# you a torn copy. `.backup` takes a consistent snapshot instead.
set -euo pipefail

cd "$(dirname "$0")"
DEST="${1:-./backups}"
STAMP="$(date +%Y-%m-%d-%H%M)"
mkdir -p "$DEST"

PYTHON="${PYTHON:-.venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON=".venv/Scripts/python.exe"
[ -x "$PYTHON" ] || PYTHON="python3"

"$PYTHON" - "$DEST/flatsplit-$STAMP.sqlite3" <<'PY'
import sqlite3, sys
source = sqlite3.connect("db.sqlite3")
target = sqlite3.connect(sys.argv[1])
with target:
    source.backup(target)
target.close(); source.close()
print(f"Database snapshot: {sys.argv[1]}")
PY

if [ -d media ] && [ -n "$(ls -A media 2>/dev/null)" ]; then
  tar -czf "$DEST/media-$STAMP.tar.gz" media
  echo "Receipts archive:  $DEST/media-$STAMP.tar.gz"
fi

# Keep the last 30 of each; a flat does not need more history than that.
ls -1t "$DEST"/flatsplit-*.sqlite3 2>/dev/null | tail -n +31 | xargs -r rm --
ls -1t "$DEST"/media-*.tar.gz 2>/dev/null | tail -n +31 | xargs -r rm --

echo "Done. Copy $DEST somewhere that is not this machine."
