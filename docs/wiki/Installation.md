# Installation

How to run Nocument with Docker (production and development) or directly on the host. All the environment variables are described in [Configuration](Configuration.md).

## Running with Docker

Docker Compose starts the app and **MongoDB**, the database of the [ContentBlocks](Content-Blocks.md). MongoDB's data stays in a volume (`mongo-data` in production, `mongo-dev-data` in development). The services talk over the `nocument-net` network, with an explicit subnet: `10.40.0.0/24` in production and `10.40.1.0/24` in development, so the two stacks can run together. If the subnet is already used by another network on the server, change it under `networks` in the Compose files.

All the environment variables, with their defaults, are listed in `.env.example`: copy it to `.env` and uncomment the ones to change. Compose uses `.env` both for the values of the compose files (ports, gunicorn workers...) and as variables of the app containers; the variables set under `environment` in the compose files (e.g. `MONGODB_URI`) win over it.

### Production

App image with the frontend (static build served by nginx) and the backend (gunicorn + LibreOffice), plus the `mongo` service (`mongo:7`). Only the frontend port is exposed; `/api` calls are forwarded to the internal backend and MongoDB is only reachable from the app. The server settings (see [Settings](Settings.md)) are kept in the `nocument-settings` volume and the [plugins](Plugins.md) in the `nocument-plugins` volume (at the first start it gets the plugins of the image).

```bash
docker compose up -d --build
```

Open `http://localhost:8080` (another port with `NOCUMENT_PORT=9000 docker compose up -d`).

The image is built without `.git`: to show its version in **Settings → Version**, pass the commit to the build:

```bash
NOCUMENT_COMMIT=$(git rev-parse HEAD) NOCUMENT_COMMIT_DATE=$(git log -1 --format=%cI) docker compose up -d --build
```

### Development

The image only contains Python, Node and LibreOffice: the libraries come from the mounted project (`.venv` and `web/node_modules`). Backend and frontend reload automatically at every change.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # once, on the host (and for every new requirement)
docker compose -f compose.dev.yaml up --build
```

Open `http://localhost:5173`. If `web/node_modules` is missing, the container runs `npm ci` at the first start. MongoDB is also published on `127.0.0.1:27017`, for a backend started on the host or for clients like MongoDB Compass. Other ports with `NOCUMENT_DEV_PORT` and `MONGODB_DEV_PORT`.

> The `.venv` points to the host interpreter (`/usr/bin/python3`, Python 3.11 of Debian 12), the same one found in the development image.

## Running locally

### Requirements

- Python 3.10+
- Node.js 20.19+ / 22.12+ and npm (required by Vite 8)
- A renderer for the Word → PDF conversion (see [PDF renderers](PDF-Renderers.md)):
  - **LibreOffice** (Linux/Windows), or
  - **Microsoft Word** (Windows only; `pywin32` is installed automatically on Windows)
- To update tables of contents with LibreOffice (Builder): on Linux the `python3-uno` package; on Windows the Python bundled with LibreOffice is found automatically

### Installation

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt   # Windows: .venv\Scripts\pip install -r requirements.txt

cd web
npm install
```

### Running

Start backend and frontend in two separate terminals.

On Windows, run `run-dev.bat` from the repository root to open both services in separate Command Prompt windows. It uses `.venv` when available (otherwise `python` from `PATH`) and starts the backend on port 5000.

The development backend listens on `NOCUMENT_BACKEND_PORT` (default 5000, address `NOCUMENT_BACKEND_HOST`, default `127.0.0.1`) and the Vite `/api` proxy forwards to the same variable, so changing it moves both. It is a separate variable from `NOCUMENT_PORT`, the port of the production web app in Docker Compose.

**Backend** (Flask, port 5000):

```bash
python -m src.app
```

The backend does not read `.env` by itself: to use the variables of `.env.example` locally, load the file in the shell first (`set -a; . ./.env; set +a; python -m src.app`).

ContentBlocks are saved in a SQLite file, `instance/nocument.sqlite3`, created at the first save: no database server is needed. To use MongoDB instead (e.g. `docker run -d -p 127.0.0.1:27017:27017 mongo:7`), set `MONGODB_URI=mongodb://localhost:27017`.

**Frontend** (Vite, port 5173; `/api` calls are forwarded to the backend by the proxy):

```bash
cd web
npm run dev
```

Open `http://localhost:5173`. To reach the development server with a host name other than `localhost`, set `NOCUMENT_DEV_ALLOWED_HOSTS` (host names separated by commas) in `.env` or in the environment of Vite.
