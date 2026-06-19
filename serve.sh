#!/usr/bin/env bash
# Local, private viewer. Binds to 127.0.0.1 only — your data never leaves the machine.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-8791}"
[ -f sources.json ] && python3 scan.py || echo "[transcrub] no sources.json — serving bundled example data"
echo "[transcrub] http://localhost:${PORT}/coread.html  (127.0.0.1 only, Ctrl-C to stop)"
exec python3 -m http.server "$PORT" --bind 127.0.0.1
