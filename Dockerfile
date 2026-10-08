# ---------- Stage 1: build the Svelte frontend ----------
FROM node:22-slim AS frontend

# Git commit of the sources (hash and ISO date), shown in Settings: the image has no .git, so they come from the build
# (see compose.yaml): NOCUMENT_COMMIT=$(git rev-parse HEAD) NOCUMENT_COMMIT_DATE=$(git log -1 --format=%cI) ...
ARG NOCUMENT_COMMIT=""
ARG NOCUMENT_COMMIT_DATE=""
ENV NOCUMENT_COMMIT=$NOCUMENT_COMMIT \
    NOCUMENT_COMMIT_DATE=$NOCUMENT_COMMIT_DATE

WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
# The translations are imported from ../locales (shared with the backend).
COPY locales/ /locales/
COPY web/ ./
RUN npm run build


# ---------- Stage 2: Flask backend + nginx serving the frontend ----------
FROM python:3.12-slim-bookworm

ARG NOCUMENT_COMMIT=""
ARG NOCUMENT_COMMIT_DATE=""
ENV NOCUMENT_COMMIT=$NOCUMENT_COMMIT \
    NOCUMENT_COMMIT_DATE=$NOCUMENT_COMMIT_DATE \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SOFFICE_PATH=/usr/bin/soffice \
    SOFFICE_TIMEOUT=120 \
    UNO_PYTHON=/usr/bin/python3

# LibreOffice (DOCX -> PDF conversion), python3-uno (table of contents update, run with the system
# python3, see UNO_PYTHON), fonts for faithful rendering, nginx for the frontend
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-writer-nogui \
        python3-uno \
        fonts-dejavu \
        fonts-liberation \
        fonts-liberation2 \
        fonts-crosextra-carlito \
        fonts-crosextra-caladea \
        nginx \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt gunicorn

COPY src/ ./src/
COPY locales/ ./locales/
# Plugins shipped with the image (e.g. the example); the folder is a volume in compose.yaml, so the plugins installed
# from the web app survive a new image.
COPY plugins/ ./plugins/

COPY --from=frontend /web/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/nocument.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

CMD ["/entrypoint.sh"]
