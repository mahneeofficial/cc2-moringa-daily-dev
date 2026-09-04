#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Moringa Daily Dev — one command to run the whole stack.
#
#   bash dev.sh        (works on Linux, macOS and Windows Git Bash)
#
# First run: creates the Python venv, installs backend + frontend deps,
# prepares/migrates the database and seeds categories + an admin account.
# Then starts the Flask API (http://localhost:5001) and the Vite client
# (http://localhost:5173). Ctrl+C stops both.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

echo "🥬 Moringa Daily Dev — starting up"

# ---------------- Python launcher ----------------
# Windows usually only has `python` (not `python3`).
PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python
command -v "$PY" >/dev/null 2>&1 || {
  echo "✖ Python not found. Install it from https://python.org and re-run."
  exit 1
}

# ---------------- Backend venv ----------------
# Windows venvs put executables in  .venv/Scripts/  (python.exe, pip.exe)
# Unix venvs put them in             .venv/bin/     (python, pip)
# Detect whichever exists — and recreate the venv if it is broken.
VENV_DIR="$(pwd)/backend/.venv"
VENV_PY=""

find_venv_python() {
  if [ -x "$VENV_DIR/bin/python" ]; then
    VENV_PY="$VENV_DIR/bin/python"
    return 0
  fi
  if [ -f "$VENV_DIR/Scripts/python.exe" ]; then
    VENV_PY="$VENV_DIR/Scripts/python.exe"
    return 0
  fi
  return 1
}

if [ ! -d backend/.venv ] || ! find_venv_python; then
  echo "→ Creating Python virtualenv (backend/.venv)…"
  rm -rf backend/.venv
  "$PY" -m venv backend/.venv
  find_venv_python || {
    echo "✖ Failed to create the virtualenv. Try: rm -rf backend/.venv && bash dev.sh"
    exit 1
  }
fi

echo "→ Installing backend dependencies…"
"$VENV_PY" -m pip install -q -r backend/requirements.txt

if [ ! -f backend/.env ]; then
  echo "→ Creating backend/.env from .env.example…"
  cp backend/.env.example backend/.env
fi

echo "→ Preparing database (fresh or existing)…"
(cd backend && "$VENV_PY" setup_db.py)

# ---------------- Frontend ----------------
if [ ! -d client/node_modules ]; then
  echo "→ Installing frontend dependencies (npm install)…"
  (cd client && npm install --silent)
fi

# ---------------- Run both ----------------
echo ""
echo "🚀 Backend  → http://localhost:5001"
echo "🚀 Frontend → http://localhost:5173"
echo "   (Ctrl+C stops both)"
echo ""

trap 'kill 0 2>/dev/null; exit 0' EXIT INT TERM
(cd backend && "$VENV_PY" run.py) &
(cd client && npm run dev -- --host 0.0.0.0) &
wait
