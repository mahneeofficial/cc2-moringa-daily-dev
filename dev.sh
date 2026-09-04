#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Moringa Daily Dev — one command to run the whole stack.
#
#   bash dev.sh
#
# First run: creates the Python venv, installs backend + frontend deps,
# prepares/migrates the database and seeds categories + an admin account.
# Then starts the Flask API (http://localhost:5001) and the Vite client
# (http://localhost:5173). Ctrl+C stops both.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

echo "🥬 Moringa Daily Dev — starting up"

# ---------------- Backend ----------------
if [ ! -d backend/.venv ]; then
  echo "→ Creating Python virtualenv (backend/.venv)…"
  python3 -m venv backend/.venv
fi

echo "→ Installing backend dependencies…"
backend/.venv/bin/pip install -q -r backend/requirements.txt

if [ ! -f backend/.env ]; then
  echo "→ Creating backend/.env from .env.example…"
  cp backend/.env.example backend/.env
fi

echo "→ Preparing database (fresh or existing)…"
(cd backend && .venv/bin/python setup_db.py)

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

trap 'kill 0' EXIT INT TERM
(cd backend && .venv/bin/python run.py) &
(cd client && npm run dev -- --host 0.0.0.0) &
wait
