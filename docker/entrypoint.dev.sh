#!/bin/sh
set -e

if [ ! -x .venv/bin/python ]; then
    echo "Missing .venv in the mounted project: create it on the host first." >&2
    exit 1
fi

if [ ! -d web/node_modules ]; then
    (cd web && npm ci)
fi

# Backend: Flask debug server with auto-reload on 127.0.0.1:${NOCUMENT_BACKEND_PORT:-5000} (reached via the Vite /api proxy)
.venv/bin/python -m src.app &

# Frontend: Vite dev server with HMR, bound to all interfaces so the browser can reach it
cd web
exec npm run dev -- --host 0.0.0.0 --port 5173
