#!/bin/sh
set -e

# Backend: internal only, reached through the nginx /api proxy
gunicorn --bind 127.0.0.1:5000 --workers "${GUNICORN_WORKERS:-2}" --timeout 180 src.app:app &

# Frontend: foreground so the container lives as long as nginx
exec nginx -g 'daemon off;'
